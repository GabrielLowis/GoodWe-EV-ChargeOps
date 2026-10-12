"""Fluxo completo com o cenário de demonstração: sessão simulada até a fatura.

Valores esperados conferidos à mão (ver docs/frente3/motor-de-rateio.md):

  Ana    S1 6,06 + S2 8,07 + S8 29,41                 = 43,54
  Bruno  S4 6,42 + S9 17,84                           = 24,26
  Carla  sem uso                                      =  0,00
  Diego  S0 13,69 (setembro/ago) + S3 9,05 + S5 0,00  = 22,74
"""


# Como ler este arquivo:
# - Aqui roda o cenário de demonstração inteiro (backend/seeds/demo.py): 5 pessoas, 10 recargas (S0 a S9)
#   e 2 anomalias, gravados no banco de teste. Os testes geram as faturas de setembro com o mesmo código
#   que o sistema usa e conferem os valores calculados à mão (a tabela acima).
# - As fixtures demo e invoices (logo abaixo) montam esse cenário. Um teste que pede "invoices" recebe as
#   faturas prontas: o pytest monta antes, sozinho, tudo de que ela depende (db -> demo -> invoices).
# - Nenhum dado é real: nomes, preços e alíquota são fictícios, e as recargas são gravadas pelo seed
#   direto no banco (não vêm da SEMS nem do simulador da Frente 1).
# - D("43.54") é um Decimal: as faturas guardam valores exatos, e a comparação é feita com Decimal também.

import copy
from datetime import date
from decimal import ROUND_HALF_UP
from decimal import Decimal as D

import pytest
from sqlalchemy import select, text

from backend.db.enums import AnomalyStatus, ChargeRule, InvoiceStatus, ValidationStatus
from backend.db.models import AuditEvent, ChargingSession, Invoice, InvoiceItem
from backend.faturamento import (
    InvoiceClosedError,
    ReviewError,
    close_invoice,
    generate_invoice,
    generate_invoices_for_period,
    revenue_report,
    review_anomaly,
)
from backend.seeds.demo import DemoIds, apply_demo_reviews, seed_demo
from backend.tests.db.factories import expect_integrity_error

# pytestmark marca TODOS os testes deste arquivo com a marca "db" (precisam do PostgreSQL).
pytestmark = pytest.mark.db

SEPTEMBER = date(2026, 9, 1)  # o mês das faturas (o período é sempre o dia 1)


# O cenário completo no banco: seed_demo grava tudo e apply_demo_reviews aplica as decisões da síndica
# (aprova a S0 e rejeita a S6). Devolve os ids gerados pelo banco, ex.: demo.sessions["S8"], demo.users["ana"].
@pytest.fixture
def demo(db) -> DemoIds:
    ids = seed_demo(db)
    apply_demo_reviews(db, ids)
    return ids


# As faturas de setembro de todo mundo, organizadas por apelido: invoices["ana"], invoices["diego"]...
# by_user transforma a lista num dicionário id -> fatura; a última linha troca o id pelo apelido do seed.
# O "if user_id in by_user" deixa de fora quem não recebeu fatura (a síndica).
@pytest.fixture
def invoices(db, demo) -> dict[str, Invoice]:
    generated = generate_invoices_for_period(db, SEPTEMBER)
    by_user = {inv.user_id: inv for inv in generated}
    return {name: by_user[user_id] for name, user_id in demo.users.items() if user_id in by_user}


# Arredonda para centavos com "meio para cima" (0,455 -> 0,46), a mesma regra do motor.
def cents(value: D) -> D:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


# O teste principal: o total de cada fatura bate com a conta feita à mão (a tabela no topo do arquivo).
def test_totais_de_setembro_batem_com_o_calculo_manual(invoices):
    assert {name: inv.total for name, inv in invoices.items()} == {
        "ana": D("43.54"),
        "bruno": D("24.26"),
        "carla": D("0.00"),
        "diego": D("22.74"),
    }


# A síndica não é moradora e não carregou: não recebe fatura (nem fatura zero).
def test_sindica_sem_sessoes_nao_recebe_fatura(invoices):
    assert "manager" not in invoices


# Carla não carregou em setembro (só teve um no-show): recebe fatura zero, com a explicação na memória de
# cálculo. Não existe mensalidade mínima.
def test_fatura_zero_para_quem_nao_carregou(invoices):
    carla = invoices["carla"]
    assert (carla.sessions_count, carla.total) == (0, D("0.00"))
    assert "Fatura zero" in carla.calculation["notes"][0]


# Ana e Bruno moram na mesma unidade (A-101), cada um com o seu carro: são duas faturas separadas, e a
# memória de cálculo de cada uma mostra a unidade.
def test_dois_veiculos_da_mesma_unidade_geram_duas_faturas(invoices):
    ana, bruno = invoices["ana"], invoices["bruno"]
    assert ana.user.unit_id == bruno.user.unit_id
    assert ana.id != bruno.id
    assert ana.calculation["user"]["unit"] == bruno.calculation["user"]["unit"] == "A-101"


# A S0 é de 28/08, mas só foi liberada em setembro (anomalia aprovada pela síndica). Ela entra na fatura de
# setembro do Diego como lançamento posterior e é cobrada com a tabela que valia em AGOSTO (versão 1, com
# overhead de 3%), e não com a de setembro. .one() exige exatamente um item com essa sessão.
def test_lancamento_posterior_usa_a_tarifa_da_data_da_sessao(db, demo, invoices):
    item = db.scalars(select(InvoiceItem).where(InvoiceItem.session_id == demo.sessions["S0"])).one()
    assert item.invoice_id == invoices["diego"].id
    assert item.is_late_entry is True
    assert item.tariff_id == demo.tariffs["v1"]  # agosto usa a versão 1 da tabela
    assert item.calculation["components"]["overhead"]["percent"] == "3.00"
    assert item.total == D("13.69")


# A S5 (falha do sistema) aparece na fatura do Diego, para ele ver o registro, mas com valor zero.
def test_falha_do_sistema_aparece_na_fatura_com_valor_zero(db, demo, invoices):
    item = db.scalars(select(InvoiceItem).where(InvoiceItem.session_id == demo.sessions["S5"])).one()
    assert item.charge_rule == ChargeRule.SYSTEM_FAILURE_NO_CHARGE
    assert item.total == D("0.00")


# A S6 (50 kWh impossíveis num carregador de 7 kW) foi rejeitada pela síndica: não vira item de fatura
# (.first() devolve None quando não acha nada), mas aparece na lista "not_included" da fatura do Diego,
# com o motivo. A lista de pares (sessão, status) precisa ter só ela.
def test_sessao_rejeitada_na_revisao_nao_e_cobrada_e_aparece_explicada(db, demo, invoices):
    assert db.scalars(select(InvoiceItem).where(InvoiceItem.session_id == demo.sessions["S6"])).first() is None
    not_included = invoices["diego"].calculation["not_included"]
    assert [(n["session_id"], n["validation_status"]) for n in not_included] == [(demo.sessions["S6"], "rejected")]


# A S7 não tem morador (nenhuma reserva corresponde a ela): não entra na fatura de ninguém.
def test_sessao_sem_morador_nao_entra_em_fatura(db, demo, invoices):
    assert db.scalars(select(InvoiceItem).where(InvoiceItem.session_id == demo.sessions["S7"])).first() is None


# Este teste monta o cenário SEM as decisões da síndica (não usa a fixture demo). Com a S0 e a S6 ainda
# suspensas, a fatura do Diego tem só a S3 (9,05) e a S5 (0,00). Depois que a síndica aprova a S0, a fatura,
# que ainda está aberta, é recalculada e chega aos 22,74 da tabela.
# {n["session_id"] for n in ...} (chaves, sem "nome: valor") monta um conjunto com os ids que ficaram de fora.
def test_sessao_suspensa_so_entra_depois_da_revisao(db):
    ids = seed_demo(db)  # sem aplicar as revisões
    diego = generate_invoice(db, ids.users["diego"], SEPTEMBER)
    assert diego.total == D("9.05")  # só S3 e S5; S0 e S6 aguardam revisão
    waiting = {n["session_id"] for n in diego.calculation["not_included"]}
    assert ids.sessions["S6"] in waiting

    review_anomaly(db, ids.anomalies["S0"], AnomalyStatus.APPROVED, ids.users["manager"], "ok")
    diego = generate_invoice(db, ids.users["diego"], SEPTEMBER)  # fatura aberta: pode recalcular
    assert diego.total == D("22.74")


# Idempotente = fazer de novo dá o mesmo resultado. Gerar outra vez a fatura aberta da Ana não cria uma
# segunda fatura (o id é o mesmo) nem muda o total ou a quantidade de sessões.
def test_recalcular_fatura_aberta_e_idempotente(db, demo, invoices):
    ana = invoices["ana"]
    before = (ana.total, ana.sessions_count)
    again = generate_invoice(db, demo.users["ana"], SEPTEMBER)
    assert again.id == ana.id
    assert (again.total, again.sessions_count) == before


# Checklist da Sprint 2: "memória de cálculo permite reproduzir o valor". Para CADA item gravado, o teste
# refaz a conta usando só o que está na memória (kWh e preço de cada trecho, base e alíquota de cada imposto)
# e compara com os valores das colunas.
# - O teste pede a fixture invoices só para as faturas existirem; os itens ele lê direto do banco.
# - "assert items" garante que a lista não está vazia (senão o for não conferiria nada e o teste passaria à toa).
# - O ", item.session_id" depois do primeiro assert do for é a mensagem mostrada se ele falhar: diz em qual
#   sessão apareceu a diferença.
def test_toda_memoria_de_calculo_reproduz_o_valor_gravado(db, invoices):
    items = db.scalars(select(InvoiceItem)).all()
    assert items
    for item in items:
        comp = item.calculation["components"]
        segments = item.calculation["band_split"]["segments"]
        green = cents(sum((D(s["green_kwh"]) * D(s["green_price_per_kwh"]) for s in segments), D(0)))
        grid = cents(sum((D(s["grid_kwh"]) * D(s["grid_price_per_kwh"]) for s in segments), D(0)))
        tax = sum((cents(D(t["base"]) * D(t["rate_percent"]) / 100) for t in comp["taxes"]), D(0))
        assert (green, grid) == (item.green_amount, item.grid_amount), item.session_id
        assert tax == item.tax_amount
        assert D(comp["total"]) == item.total


# Como o banco entrega as datas depende do fuso da CONEXÃO. Este teste gera a fatura do Diego duas vezes,
# com a conexão em UTC e depois em horário de Brasília, e exige memórias de cálculo idênticas. A fatura do
# Diego foi escolhida porque reúne os casos mais delicados: a S0 (de agosto, com a tarifa antiga), a S3,
# a S5 (falha) e a S6 (rejeitada, que aparece na lista not_included).
# - set_config('TimeZone', ..., true) muda o fuso só até o fim desta transação (é o que o true indica).
# - expire_all() faz o SQLAlchemy esquecer o que já tinha lido e buscar tudo de novo, já no novo fuso.
# - copy.deepcopy tira uma "foto" completa das memórias, que o segundo cálculo não consegue mais alterar.
# - [invoice.calculation, *(...)] monta uma lista com a memória da fatura seguida da memória de cada item
#   (o * "espalha" os itens dentro da lista). Os itens vão em ordem de sessão, para a comparação ser justa.
def test_memoria_de_calculo_nao_depende_do_fuso_da_conexao(db, demo):
    """O PostgreSQL devolve as datas no fuso da conexão: UTC no Docker, horário de Brasília num
    PostgreSQL instalado no Windows. A memória de cálculo precisa sair igual nos dois casos."""

    def memory_with_timezone(zone: str) -> list:
        db.execute(text("SELECT set_config('TimeZone', :zone, true)"), {"zone": zone})
        db.expire_all()  # obriga a reler tudo do banco
        invoice = generate_invoice(db, demo.users["diego"], SEPTEMBER)  # itens S0, S3, S5; S6 em not_included
        items = sorted(invoice.items, key=lambda i: i.session_id)
        return copy.deepcopy([invoice.calculation, *(i.calculation for i in items)])

    assert memory_with_timezone("UTC") == memory_with_timezone("America/Sao_Paulo")


# Fechar a fatura da Ana (close_invoice, como o síndico faria) tem três efeitos, conferidos em ordem:
#   1. gerar de novo dá InvoiceClosedError: o sistema se recusa a recalcular;
#   2. nem um UPDATE direto no banco muda os valores: o gatilho recusa. O UPDATE zera todos os valores
#      juntos para a conta continuar coerente; a única coisa errada nele é mexer numa fatura fechada;
#   3. a auditoria registrou a geração ("invoice_generated") e o fechamento ("invoice_closed").
# "with pytest.raises(Erro):" só deixa o teste seguir se o código dentro do bloco lançar esse erro.
# As três strings seguidas dentro de text(...) são coladas pelo Python numa só (é um SQL longo quebrado em linhas).
def test_fechamento_torna_a_fatura_imutavel(db, demo, invoices):
    ana = close_invoice(db, invoices["ana"].id, demo.users["manager"])
    assert ana.status == InvoiceStatus.CLOSED
    with pytest.raises(InvoiceClosedError):
        generate_invoice(db, demo.users["ana"], SEPTEMBER)
    expect_integrity_error(
        db,
        lambda: db.execute(
            text(
                "UPDATE invoices SET total = 0, subtotal = 0, green_amount = 0, "
                "grid_amount = 0, idle_amount = 0, tax_amount = 0, overhead_amount = 0 "
                "WHERE id = :i"
            ),
            {"i": ana.id},
        ),
        "fechada",
    )
    actions = db.scalars(
        select(AuditEvent.action).where(AuditEvent.entity_type == "invoice", AuditEvent.entity_id == str(ana.id))
    ).all()
    assert "invoice_generated" in actions and "invoice_closed" in actions


# O ciclo completo de uma liberação tardia:
#   1. a fatura de setembro do Diego é gerada com a S0 ainda suspensa (9,05) e é FECHADA;
#   2. só depois a síndica aprova a S0;
#   3. a fatura de outubro recebe a S0 como lançamento posterior, com a tarifa de agosto (13,69);
#   4. setembro continua 9,05: fatura fechada não muda;
#   5. novembro não tem nada: a S0 não é cobrada duas vezes.
# "[item] = october.items" desempacota a lista e, de quebra, exige que ela tenha exatamente um item.
# db.refresh(september) relê a fatura de setembro do banco antes de conferir.
def test_sessao_liberada_depois_do_fechamento_vai_para_o_mes_seguinte(db):
    ids = seed_demo(db)  # S0 (agosto) ainda suspensa
    september = generate_invoice(db, ids.users["diego"], SEPTEMBER)
    close_invoice(db, september.id, ids.users["manager"])
    review_anomaly(db, ids.anomalies["S0"], AnomalyStatus.APPROVED, ids.users["manager"], "ok")

    october = generate_invoice(db, ids.users["diego"], date(2026, 10, 1))
    [item] = october.items
    assert item.session_id == ids.sessions["S0"]
    assert item.is_late_entry is True
    assert item.total == D("13.69")  # tarifa de agosto (versão 1)
    db.refresh(september)
    assert september.total == D("9.05")  # a fatura fechada não mudou

    november = generate_invoice(db, ids.users["diego"], date(2026, 11, 1))
    assert november.sessions_count == 0  # nenhuma sessão é cobrada duas vezes


# Regras da revisão de anomalia: a moradora Ana não pode revisar (ReviewError com "síndico" na mensagem);
# a síndica rejeita a S6; uma segunda revisão da mesma anomalia é recusada ("já foi revisada"). No fim, a
# sessão continua rejeitada. db.get(Classe, id) busca um registro pela chave primária.
def test_revisao_de_anomalia_exige_sindico_e_so_acontece_uma_vez(db):
    ids = seed_demo(db)
    with pytest.raises(ReviewError, match="síndico"):
        review_anomaly(db, ids.anomalies["S6"], AnomalyStatus.REJECTED, ids.users["ana"])
    review_anomaly(db, ids.anomalies["S6"], AnomalyStatus.REJECTED, ids.users["manager"], "medição impossível")
    with pytest.raises(ReviewError, match="já foi revisada"):
        review_anomaly(db, ids.anomalies["S6"], AnomalyStatus.APPROVED, ids.users["manager"])
    assert db.get(ChargingSession, ids.sessions["S6"]).validation_status == ValidationStatus.REJECTED


# O relatório de arrecadação do mês fecha nos dois sentidos:
# - dinheiro: o total do relatório é a soma das 4 faturas, e o reembolso de energia ao condomínio é a soma
#   das parcelas Green + Grid;
# - energia: cada kWh entregue em setembro cai em exatamente um "balde" (faturado, falha do sistema,
#   aguardando revisão, rejeitado, sem morador, aprovado e não faturado), e os baldes somam os 144,800 kWh
#   entregues. Os 19,5 kWh da S0 ficam fora dessa soma porque a recarga é de agosto; ela aparece à parte,
#   como lançamento posterior de R$ 13,69. Rejeitado = S6 (50 kWh); sem morador = S7 (6,5 kWh).
# "a == b == c" confere as duas igualdades de uma vez.
def test_relatorio_de_arrecadacao_fecha_com_as_faturas_e_com_a_energia(db, invoices):
    report = revenue_report(db, SEPTEMBER)
    assert D(report["totals"]["total"]) == sum(inv.total for inv in invoices.values())
    assert report["totals"]["invoices_count"] == 4
    reimbursement = report["condominium_reimbursement"]
    assert D(reimbursement["energy_amount"]) == sum(inv.green_amount + inv.grid_amount for inv in invoices.values())

    balance = report["energy_balance"]
    buckets = [
        "billed",
        "system_failure_not_charged",
        "waiting_review",
        "rejected",
        "unattributed",
        "approved_not_invoiced",
    ]
    assert sum(D(balance[b]["kwh"]) for b in buckets) == D(balance["delivered_kwh"]) == D("144.800")
    assert balance["rejected"]["kwh"] == "50.000"
    assert balance["unattributed"]["kwh"] == "6.500"
    assert balance["late_entries_from_previous_periods"]["amount"] == "13.69"
