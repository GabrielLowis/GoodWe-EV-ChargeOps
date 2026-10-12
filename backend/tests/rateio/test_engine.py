"""Motor de rateio: fórmula, casos excepcionais e memória de cálculo (sem banco)."""

# Como ler este arquivo:
# - Cada teste monta uma sessão com make_session (helpers.py), chama calculate_session e confere o
#   resultado com assert. Não há banco: tudo acontece na memória, em milissegundos.
# - tariff e iss_5 são fixtures do conftest.py: a tabela de demonstração (kWh da rede: R$ 0,65 fora de
#   ponta, R$ 0,95 no intermediário e R$ 1,45 na ponta; kWh solar: R$ 0,30; ociosidade: R$ 0,25/min;
#   overhead: 5%) e o ISS de 5%. O pytest entrega cada uma ao teste que tiver um parâmetro com esse nome.
# - calculate_session(sessão, tarifa, impostos, feriados, fuso) recebe sempre nesta ordem.
#   [] = nenhum imposto; NO_HOLIDAYS = nenhum feriado; TZ = fuso do condomínio.
# - Os valores esperados foram calculados à mão, e as contas estão nos comentários de cada teste.
# - Os valores em reais vêm como Decimal: D("27.06") é R$ 27,06 exatos.

# replace (de dataclasses) cria uma cópia de uma "ficha" congelada trocando só alguns campos.
from dataclasses import replace
from datetime import UTC, timedelta
from decimal import ROUND_HALF_UP
from decimal import Decimal as D

import pytest

from backend.db.enums import ChargeRule, SessionEndStatus, ValidationStatus
from backend.rateio.engine import calculate_session, summarize_invoice
from backend.rateio.models import BandPrice, PowerSample, SessionNotBillableError, TaxRuleSpec
from backend.tests.helpers import TZ, at, build_tariff, make_session

NO_HOLIDAYS: frozenset = frozenset()  # conjunto vazio: nenhum feriado


# Arredonda para centavos com "meio para cima" (1,4155 -> 1,42), a mesma regra do motor.
def cents(value: D) -> D:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


# O exemplo do plano da Sprint 2: numa segunda-feira, carga das 17:30 às 20:30 (começa no intermediário e
# passa para a ponta às 18:00), 19,8 kWh da rede, e o carro só sai às 20:50 (20 minutos parado).
# Os testes mudam o que precisarem: plan_example(end_status=...) troca só o status.
def plan_example(**overrides):
    """Exemplo do plano: 17:30 às 20:30 (intermediário -> ponta), carro sai às 20:50."""
    data = dict(
        started_at=at(21, 17, 30),
        energy_ended_at=at(21, 20, 30),
        ended_at=at(21, 20, 50),
        total_kwh=D("19.800"),
        green_kwh=D("0.000"),
        grid_kwh=D("19.800"),
    )
    data.update(overrides)
    return make_session(**data)


# --- Fórmula principal ---------------------------------------------------------------------
# O caso mais importante: o exemplo do plano calculado faixa por faixa, com as contas linha a linha abaixo.
# No fim, confere também a divisão gravada na memória de cálculo: uma lista de pares (faixa, kWh da rede).
def test_exemplo_do_plano_calculado_por_faixa(tariff, iss_5):
    charge = calculate_session(plan_example(), tariff, iss_5, NO_HOLIDAYS, TZ)
    # Sem curva: 30 min (1/6) no intermediário e 150 min (5/6) na ponta
    #   3,300 kWh x 0,95 = 3,1350  |  16,500 kWh x 1,45 = 23,9250  ->  Grid = 27,06
    # Ociosidade: 20 min - 15 de tolerância = 5 min x 0,25 = 1,25
    # Subtotal 28,31 | ISS 5% = 1,4155 -> 1,42 | Overhead 5% = 1,42 | Total 31,15
    assert charge.green_amount == D("0.00")
    assert charge.grid_amount == D("27.06")
    assert charge.idle_amount == D("1.25")
    assert charge.subtotal == D("28.31")
    assert charge.tax_amount == D("1.42")
    assert charge.overhead_amount == D("1.42")
    assert charge.total == D("31.15")
    segments = charge.calculation["band_split"]["segments"]
    assert [(s["band"], s["grid_kwh"]) for s in segments] == [("intermediate", "3.300"), ("peak", "16.500")]


# Regra da Sprint 2: nunca usar a faixa do horário de início para a sessão inteira. Se o motor fizesse
# isso, cobraria tudo como intermediário (19,8 x 0,95 = 18,81). O certo, trecho a trecho, é 27,06.
def test_nao_usa_a_tarifa_do_horario_inicial_para_a_sessao_inteira(tariff):
    charge = calculate_session(plan_example(), tariff, [], NO_HOLIDAYS, TZ)
    start_band_only = cents(D("19.8") * D("0.95"))  # tudo como intermediário = 18,81
    assert charge.grid_amount != start_band_only
    assert charge.grid_amount == D("27.06")


# Energia solar (Green) e energia da rede (Grid) têm preços diferentes na mesma faixa: das 10h às 12h tudo
# é fora de ponta, e os 10 kWh são cobrados separados por origem.
def test_green_e_grid_tem_precos_diferentes(tariff):
    session = make_session(total_kwh=D("10"), green_kwh=D("4"), grid_kwh=D("6"))  # 10h-12h fora de ponta
    charge = calculate_session(session, tariff, [], NO_HOLIDAYS, TZ)
    assert charge.green_amount == D("1.20")  # 4 x 0,30
    assert charge.grid_amount == D("3.90")  # 6 x 0,65


# Imposto e overhead são calculados sobre o subtotal (energia + ociosidade), cada um arredondado aos
# centavos. TaxRuleSpec("icms", D("18"), id=7) = tipo, alíquota de 18% (valor só de teste) e um id qualquer.
# tax_rule_ids guarda quais impostos foram usados; (7,) é uma tupla de um elemento só (a vírgula é obrigatória).
def test_imposto_e_overhead_incidem_sobre_o_subtotal(tariff):
    session = make_session()  # 14 kWh da rede fora de ponta = 9,10
    taxes = [TaxRuleSpec("icms", D("18"), id=7)]
    charge = calculate_session(session, tariff, taxes, NO_HOLIDAYS, TZ)
    assert charge.subtotal == D("9.10")
    assert charge.tax_amount == D("1.64")  # 9,10 x 18% = 1,638
    assert charge.overhead_amount == D("0.46")  # 9,10 x 5% = 0,455 -> meio para cima
    assert charge.total == D("11.20")
    assert charge.tax_rule_ids == (7,)


# A assembleia pode decidir não cobrar overhead: com 0%, essa parcela sai R$ 0,00.
def test_overhead_pode_ser_zero(iss_5):
    charge = calculate_session(make_session(), build_tariff(overhead="0"), iss_5, NO_HOLIDAYS, TZ)
    assert charge.overhead_amount == D("0.00")


# Na transição da reforma tributária podem valer dois impostos ao mesmo tempo (CBS 0,9% e IBS 0,1%, valores
# de teste). Cada um é calculado e arredondado separadamente sobre os 9,10: 0,0819 -> 0,08 e 0,0091 -> 0,01.
# A memória de cálculo mostra uma linha por imposto, com o valor em texto.
def test_varios_impostos_na_transicao_ibs_cbs(tariff):
    taxes = [TaxRuleSpec("cbs", D("0.9"), id=1), TaxRuleSpec("ibs", D("0.1"), id=2)]
    charge = calculate_session(make_session(), tariff, taxes, NO_HOLIDAYS, TZ)
    rows = charge.calculation["components"]["taxes"]
    assert [(r["tax_type"], r["amount"]) for r in rows] == [("cbs", "0.08"), ("ibs", "0.01")]
    assert charge.tax_amount == D("0.09")


# Se a regra do imposto mandar excluir a energia compensada (a solar, Green), a base do imposto é o
# subtotal menos a parcela Green: 5,10 - 1,20 = 3,90. E 10% de 3,90 = 0,39.
def test_exclusao_da_energia_compensada_da_base_do_imposto(tariff):
    session = make_session(total_kwh=D("10"), green_kwh=D("4"), grid_kwh=D("6"))  # Green 1,20 + Grid 3,90
    taxes = [TaxRuleSpec("cbs", D("10"), exclude_compensated_energy=True, id=3)]
    charge = calculate_session(session, tariff, taxes, NO_HOLIDAYS, TZ)
    row = charge.calculation["components"]["taxes"][0]
    assert row["base"] == "3.90"  # subtotal 5,10 - Green 1,20
    assert charge.tax_amount == D("0.39")


# A mesma carga (18:30 às 20:00, 1 kWh solar + 8 kWh da rede) em dois dias: 07/09, feriado da
# Independência (uma segunda-feira), e 21/09, uma segunda comum. No feriado é tudo fora de ponta;
# na segunda comum, das 18:30 às 20:00 é ponta. frozenset({...}) é o conjunto de feriados: só o 07/09.
def test_feriado_sai_mais_barato_que_segunda_comum(tariff):
    holiday_session = make_session(
        started_at=at(7, 18, 30),
        energy_ended_at=at(7, 20),
        ended_at=at(7, 20),
        total_kwh=D("9"),
        green_kwh=D("1"),
        grid_kwh=D("8"),
    )
    regular_session = make_session(
        started_at=at(21, 18, 30),
        energy_ended_at=at(21, 20),
        ended_at=at(21, 20),
        total_kwh=D("9"),
        green_kwh=D("1"),
        grid_kwh=D("8"),
    )
    independencia = frozenset({at(7, 0).date()})
    on_holiday = calculate_session(holiday_session, tariff, [], independencia, TZ)
    on_monday = calculate_session(regular_session, tariff, [], independencia, TZ)
    assert on_holiday.subtotal == D("5.50")  # 1 x 0,30 + 8 x 0,65
    assert on_monday.subtotal == D("11.90")  # 1 x 0,30 + 8 x 1,45


# --- Casos excepcionais da Sprint 1 --------------------------------------------------------
# Falha do sistema (código E-COMM): a sessão sai com a regra "system_failure_no_charge" e tudo zerado.
# A memória de cálculo guarda quanto foi entregue sem cobrança e o motivo (o código aparece na explicação).
# "a == b == c" confere as duas igualdades de uma vez.
def test_falha_do_sistema_gera_linha_zerada_com_motivo(tariff, iss_5):
    session = plan_example(end_status=SessionEndStatus.SYSTEM_FAILURE, failure_code="E-COMM")
    charge = calculate_session(session, tariff, iss_5, NO_HOLIDAYS, TZ)
    assert charge.charge_rule == ChargeRule.SYSTEM_FAILURE_NO_CHARGE
    assert charge.total == D("0.00")
    assert charge.green_kwh == charge.grid_kwh == D("0.000")
    assert charge.calculation["components"]["grid"]["delivered_not_charged_kwh"] == "19.800"
    assert "E-COMM" in charge.calculation["explanation"][0]


# O morador encerrou a sessão: paga a energia (27,06, como no exemplo do plano), mas não paga
# ociosidade, mesmo tendo saído só às 22:00 (90 minutos depois do fim da energia).
def test_encerrada_pelo_morador_paga_so_a_energia(tariff):
    session = plan_example(end_status=SessionEndStatus.USER_STOPPED, ended_at=at(21, 22))
    charge = calculate_session(session, tariff, [], NO_HOLIDAYS, TZ)
    assert charge.charge_rule == ChargeRule.USER_STOPPED_NO_IDLE
    assert charge.grid_amount == D("27.06")
    assert charge.idle_amount == D("0.00")


# Sessões que o motor se recusa a cobrar. Cada linha da lista é um caso: o que muda na sessão padrão e o
# código de erro esperado (6 execuções do mesmo teste):
#   suspensa, pendente ou rejeitada -> "not_approved" (só sessão aprovada é cobrada)
#   sem morador                     -> "unattributed"
#   ainda em andamento              -> "in_progress"
#   Green 5 + Grid 5 = 10, mas o total diz 14 -> "energy_balance" (as contas não fecham)
# "as error" guarda o erro capturado, para o assert do fim conferir o código.
@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"validation_status": ValidationStatus.SUSPENDED}, "not_approved"),
        ({"validation_status": ValidationStatus.PENDING}, "not_approved"),
        ({"validation_status": ValidationStatus.REJECTED}, "not_approved"),
        ({"user_id": None}, "unattributed"),
        ({"end_status": SessionEndStatus.IN_PROGRESS, "ended_at": None}, "in_progress"),
        ({"green_kwh": D("5"), "grid_kwh": D("5"), "total_kwh": D("14")}, "energy_balance"),
    ],
)
def test_sessoes_que_o_motor_recusa(tariff, overrides, code):
    with pytest.raises(SessionNotBillableError) as error:
        calculate_session(make_session(**overrides), tariff, [], NO_HOLIDAYS, TZ)
    assert error.value.code == code


# O limite físico é potência x tempo, com 5% de margem: 7 kW x 1,5 h x 1,05 = cerca de 11 kWh.
# 50 kWh passa muito disso: o motor recusa com o código "physically_impossible".
def test_energia_fisicamente_impossivel_e_recusada(tariff):
    """Exemplo da Sprint 1: 50 kWh em 90 min num carregador de 7 kW (máximo ~10,5 kWh)."""
    session = make_session(
        started_at=at(15, 20),
        energy_ended_at=at(15, 21, 30),
        ended_at=at(15, 21, 30),
        total_kwh=D("50"),
        grid_kwh=D("50"),
    )
    with pytest.raises(SessionNotBillableError) as error:
        calculate_session(session, tariff, [], NO_HOLIDAYS, TZ)
    assert error.value.code == "physically_impossible"


# Green + Grid (5,70) difere do total (5,71) em só 0,01 kWh, dentro da tolerância de 0,05 kWh. A sessão é
# cobrada pelos campos Green e Grid, e a memória de cálculo ganha uma observação ("notes" não fica vazio).
def test_pequena_diferenca_de_arredondamento_da_sems_e_aceita(tariff):
    # Frente 2 observou 5,70 kWh Green e 5,71 kWh no total
    session = make_session(total_kwh=D("5.71"), green_kwh=D("5.70"), grid_kwh=D("0.00"))
    charge = calculate_session(session, tariff, [], NO_HOLIDAYS, TZ)
    assert charge.green_amount == D("1.71")  # 5,70 x 0,30
    assert charge.calculation["notes"]


# .replace(tzinfo=None) tira o fuso da data. Sem fuso não dá para saber que horas eram no condomínio,
# então o motor recusa com o código "naive_datetime" (data "ingênua", no jargão do Python).
def test_data_sem_fuso_e_recusada(tariff):
    naive = at(21, 10).replace(tzinfo=None)
    with pytest.raises(SessionNotBillableError) as error:
        calculate_session(make_session(started_at=naive), tariff, [], NO_HOLIDAYS, TZ)
    assert error.value.code == "naive_datetime"


# --- Memória de cálculo --------------------------------------------------------------------
# A sessão do exemplo do plano, agora com curva de potência: uma leitura a cada 5 minutos, com queda no
# final. A lista tem 37 potências: 6,6 kW, depois 30 vezes 6,9 kW, e a descida de 6,0 até 0,0.
# enumerate dá a posição i de cada potência, e a leitura i fica em 17:30 + 5 x i minutos.
# O teste refaz a conta inteira usando SÓ a memória de cálculo (kWh e preço de cada trecho, minutos e
# preço da ociosidade, base e alíquota dos impostos, percentual de overhead) e confere que chega aos
# mesmos valores cobrados. É isso que permite a qualquer pessoa conferir a fatura depois.
def test_memoria_de_calculo_reproduz_o_valor(tariff, iss_5):
    """Checklist da Sprint 2: 'Memória de cálculo permite reproduzir o valor'."""
    samples = tuple(
        PowerSample(at(21, 17, 30) + timedelta(minutes=5 * i), D(v))
        for i, v in enumerate(["6.6"] + ["6.9"] * 30 + ["6.0", "5.0", "4.0", "3.0", "2.0", "0.0"])
    )
    session = plan_example(total_kwh=D("19.2"), green_kwh=D("0.6"), grid_kwh=D("18.6"), power_samples=samples)
    charge = calculate_session(session, tariff, iss_5, NO_HOLIDAYS, TZ)
    memory = charge.calculation
    comp = memory["components"]

    # A conta refeita com os números da memória:
    segments = memory["band_split"]["segments"]
    green = cents(sum(D(s["green_kwh"]) * D(s["green_price_per_kwh"]) for s in segments))
    grid = cents(sum(D(s["grid_kwh"]) * D(s["grid_price_per_kwh"]) for s in segments))
    idle = cents(D(comp["idle"]["billable_minutes"]) * D(comp["idle"]["fee_per_minute"]))
    subtotal = green + grid + idle
    tax = sum(cents(D(t["base"]) * D(t["rate_percent"]) / 100) for t in comp["taxes"])
    overhead = cents(subtotal * D(comp["overhead"]["percent"]) / 100)

    # E a comparação com o que o motor cobrou:
    assert memory["band_split"]["method"] == "power_curve"
    assert sum(D(s["green_kwh"]) for s in segments) == D("0.600")
    assert sum(D(s["grid_kwh"]) for s in segments) == D("18.600")
    assert (green, grid, idle) == (charge.green_amount, charge.grid_amount, charge.idle_amount)
    assert subtotal == charge.subtotal == D(comp["subtotal"]["amount"])
    assert tax == charge.tax_amount
    assert overhead == charge.overhead_amount
    assert subtotal + tax + overhead == charge.total == D(comp["total"])
    assert memory["tariff"]["prices"]["peak"]["grid_price_per_kwh"] == "1.4500"  # cópia da tarifa usada


# replace cria duas cópias da tarifa de teste:
# - from_python, como o Python costuma guardar: preço 1.45 e data com -03:00;
# - from_db, como o banco devolve: quantize(D("0.0001")) força 4 casas (1.4500) e a data vem em UTC,
#   que é o mesmo instante escrito de outro jeito (01/09 00:00 em Brasília = 01/09 03:00 em UTC).
# As duas cópias gravadas na memória de cálculo (snapshot) precisam sair idênticas.
def test_copia_da_tarifa_sai_igual_venha_do_banco_ou_da_memoria(tariff):
    """O banco devolve 1.4500 e datas no fuso da conexão; na memória do Python pode estar 1.45 e -03:00.

    A cópia da tarifa gravada na memória de cálculo precisa sair igual nos dois casos.
    """
    from_python = replace(tariff, valid_from=at(1, 0))  # 01/09/2026 00:00, horário local
    from_db = replace(
        tariff,
        prices={
            band: BandPrice(p.green_price_per_kwh.quantize(D("0.0001")), p.grid_price_per_kwh.quantize(D("0.0001")))
            for band, p in tariff.prices.items()
        },
        idle_fee_per_minute=tariff.idle_fee_per_minute.quantize(D("0.0001")),
        overhead_percent=tariff.overhead_percent.quantize(D("0.01")),
        valid_from=at(1, 0).astimezone(UTC),  # o mesmo instante, escrito em UTC
    )
    assert from_python.snapshot(TZ) == from_db.snapshot(TZ)
    saved = from_db.snapshot(TZ)
    assert saved["valid_from"] == "2026-09-01T00:00:00-03:00"
    assert saved["prices"]["peak"]["grid_price_per_kwh"] == "1.4500"
    assert saved["idle_fee_per_minute"] == "0.2500"


# --- Fatura mensal -------------------------------------------------------------------------
# summarize_invoice soma as sessões do mês e as contas da fatura continuam fechando:
# subtotal = Green + Grid + ociosidade, e total = subtotal + imposto + overhead.
def test_fatura_soma_as_sessoes(tariff, iss_5):
    first = calculate_session(plan_example(session_id=1), tariff, iss_5, NO_HOLIDAYS, TZ)
    second = calculate_session(
        make_session(session_id=2, started_at=at(22, 10), energy_ended_at=at(22, 12), ended_at=at(22, 12)),
        tariff,
        iss_5,
        NO_HOLIDAYS,
        TZ,
    )
    totals = summarize_invoice([first, second])
    assert totals.sessions_count == 2
    assert totals.total == first.total + second.total
    assert totals.subtotal == totals.green_amount + totals.grid_amount + totals.idle_amount
    assert totals.total == totals.subtotal + totals.tax_amount + totals.overhead_amount


# Sem sessões, a fatura é zero: não existe mensalidade mínima.
def test_morador_que_nao_carregou_tem_fatura_zero():
    totals = summarize_invoice([])
    assert totals.sessions_count == 0
    assert totals.total == D("0.00")

