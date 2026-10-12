## Regras de integridade do plano da Sprint 2, garantidas pelo PostgreSQL. ##

""" 1. Uma sessão não pode ser cobrada para dois moradores ao mesmo tempo.
2. Reservas do mesmo carregador não se sobrepõem além da capacidade configurada.
3. Tarifas versionadas / com validade temporal (fatura antiga reproduzível).
4. Fatura fechada não muda silenciosamente.
5. Toda revisão manual de anomalia deixa evento de auditoria.
"""

# Como ler este arquivo:
# - Quase todo teste segue o mesmo roteiro: grava um cenário válido com as fábricas (factories.py), tenta
#   uma operação proibida e exige, com expect_integrity_error, que o PRÓPRIO BANCO a recuse.
# - O texto no fim de cada expect_integrity_error é um pedaço da mensagem de erro esperada: o nome da
#   regra (ex.: "ex_reservations_no_overlap") ou uma frase da mensagem do gatilho (ex.: "fechada"). Assim
#   o teste confirma que a recusa veio da regra certa, e não de outro problema qualquer.
# - db e base são fixtures (veja os dois conftest.py): db é a sessão isolada, desfeita no fim de cada
#   teste, e base é o cadastro mínimo (Ana, Bruno, a síndica, os carregadores T1 e T2, a tarifa e o ISS).
# - at(21, 19) = 21/09/2026 às 19:00, uma segunda-feira, no fuso do condomínio.
# - As regras em si (CHECK, EXCLUDE, chaves e gatilhos) estão na migration 0001_schema_inicial.py:
#   procure lá o nome que aparece em cada teste.

from decimal import Decimal as D

import pytest

# func.count() é o COUNT(*) do SQL; select monta consultas; text envia um SQL escrito à mão.
from sqlalchemy import func, select, text

from backend.db.enums import AnomalyStatus, AttributionMethod, InvoiceStatus, ReservationStatus, ValidationStatus
from backend.db.models import Anomaly, AuditEvent, ChargingSession, Invoice, Tariff, TariffBand, TariffWindow
from backend.tests.db.factories import (
    charging_session,
    expect_integrity_error,
    item,
    open_invoice,
    reserve,
)
from backend.tests.helpers import at

# pytestmark marca TODOS os testes deste arquivo com a marca "db" (precisam do PostgreSQL).
pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Regra 2 - reservas e capacidade
# ---------------------------------------------------------------------------
# Ana reservou o T1 das 19h às 21h. Bruno tenta das 20h às 22h no mesmo conector: as duas disputariam a
# hora das 20h às 21h, e o banco recusa a segunda (ex_reservations_no_overlap).
def test_reservas_sobrepostas_no_mesmo_conector_sao_recusadas(db, base):
    reserve(db, base.ana, base.charger, at(21, 19), at(21, 21))
    expect_integrity_error(
        db, lambda: reserve(db, base.bruno, base.charger, at(21, 20), at(21, 22)), "ex_reservations_no_overlap"
    )


# Encostar pode: uma termina às 21h e a outra começa às 21h. O intervalo é [início, fim): o início conta e
# o fim não, então as duas não têm nenhum minuto em comum. Este teste não tem assert: ele passa se nenhuma
# das duas reservas der erro.
def test_reservas_encostadas_sao_permitidas(db, base):
    reserve(db, base.ana, base.charger, at(21, 19), at(21, 21))
    reserve(db, base.bruno, base.charger, at(21, 21), at(21, 23))  # intervalo [início, fim)


# Reserva cancelada deixa de ocupar o horário: a regra de sobreposição só olha as reservas ativas ou em uso
# (o WHERE da regra, na migration). Depois do cancelamento, Bruno consegue exatamente o mesmo horário.
def test_reserva_cancelada_libera_o_horario(db, base):
    first = reserve(db, base.ana, base.charger, at(21, 19), at(21, 21))
    first.status = ReservationStatus.CANCELLED
    db.flush()
    reserve(db, base.bruno, base.charger, at(21, 19), at(21, 21))


# O T2 tem 2 conectores: Ana (conector 1) e Bruno (conector 2) reservam o mesmo horário sem conflito.
# A síndica tenta o conector 3, que não existe: o gatilho de capacidade recusa (a mensagem dele fala em
# "capacidade configurada").
def test_capacidade_configurada_de_dois_conectores(db, base):
    reserve(db, base.ana, base.charger2, at(21, 19), at(21, 21), connector=1)
    reserve(db, base.bruno, base.charger2, at(21, 19), at(21, 21), connector=2)
    # não existe terceiro conector: o gatilho de capacidade recusa
    expect_integrity_error(
        db, lambda: reserve(db, base.manager, base.charger2, at(21, 19), at(21, 21), connector=3), "capacidade"
    )


# ---------------------------------------------------------------------------
# Sessões: regra física e atribuição
# ---------------------------------------------------------------------------
# A mesma recarga pode ser registrada por duas fontes (aqui, "sems" e "gateway"), com horários que diferem
# por segundos (19:00:03 e 21:00:02). Como as duas ocupariam o mesmo conector ao mesmo tempo, o banco
# recusa a segunda (ex_sessions_no_overlap), e a recarga não é contada duas vezes.
# O teste monta a segunda sessão direto com ChargingSession(...), sem fábrica, para controlar cada campo.
def test_mesma_recarga_vinda_da_sems_e_do_gateway_nao_e_gravada_duas_vezes(db, base):
    charging_session(db, base, base.ana, at(21, 19), at(21, 21), source="sems", external_id="sems-1")
    duplicate = ChargingSession(
        source="gateway",
        external_id="gw-1",
        charger_id=base.charger.id,
        started_at=at(21, 19, 0, second=3),
        ended_at=at(21, 21, 0, second=2),
        end_status="completed",
    )
    expect_integrity_error(db, lambda: db.add(duplicate), "ex_sessions_no_overlap")


# A sessão aponta para a reserva da Ana, mas diz que o morador é o Bruno. A chave composta
# (reservation_id, user_id) exige que esse par exista em reservations, e o par (reserva da Ana, Bruno)
# não existe: o banco recusa (fk_sessions_reservation_same_user).
def test_sessao_atribuida_por_reserva_pertence_ao_dono_da_reserva(db, base):
    reservation = reserve(db, base.ana, base.charger, at(21, 19), at(21, 21), status=ReservationStatus.COMPLETED)
    wrong_owner = ChargingSession(
        source="simulator",
        external_id="x",
        charger_id=base.charger.id,
        reservation_id=reservation.id,
        user_id=base.bruno.id,
        attribution_method=AttributionMethod.RESERVATION,
        started_at=at(21, 19),
        ended_at=at(21, 21),
        end_status="completed",
    )
    expect_integrity_error(db, lambda: db.add(wrong_owner), "fk_sessions_reservation_same_user")


# Contradição: a sessão tem morador (a Ana), mas está marcada como "não atribuída". A regra
# ck_sessions_attribution_user exige as duas coisas juntas: não atribuída <=> sem morador.
def test_sessao_com_morador_nao_pode_estar_como_nao_atribuida(db, base):
    inconsistent = ChargingSession(
        source="simulator",
        external_id="y",
        charger_id=base.charger.id,
        user_id=base.ana.id,
        attribution_method=AttributionMethod.UNATTRIBUTED,
        started_at=at(21, 19),
        ended_at=at(21, 21),
        end_status="completed",
    )
    expect_integrity_error(db, lambda: db.add(inconsistent), "ck_sessions_attribution_user")


# A energia não pode parar (22h) depois de o carro ser desconectado (21h): ck_sessions_energy_end_order.
def test_fim_da_energia_nao_pode_ser_depois_da_desconexao(db, base):
    bad = ChargingSession(
        source="simulator",
        external_id="z",
        charger_id=base.charger.id,
        started_at=at(21, 19),
        energy_ended_at=at(21, 22),
        ended_at=at(21, 21),
        end_status="completed",
    )
    expect_integrity_error(db, lambda: db.add(bad), "ck_sessions_energy_end_order")


# ---------------------------------------------------------------------------
# Regra 1 - uma sessão, um morador, uma cobrança
# ---------------------------------------------------------------------------
# A sessão é da Ana, mas alguém tenta cobrá-la na fatura do Bruno. O item recebe o user_id da fatura
# (Bruno), e a chave (session_id, user_id) procura em charging_sessions essa sessão com o Bruno como
# morador. Não existe: o banco recusa (fk_items_session_same_user).
def test_sessao_nao_pode_ser_cobrada_na_fatura_de_outro_morador(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    bruno_invoice = open_invoice(db, base.bruno)
    expect_integrity_error(
        db, lambda: bruno_invoice.items.append(item(bruno_invoice, session)), "fk_items_session_same_user"
    )


# A sessão já está na fatura de setembro; colocá-la também na de outubro seria cobrar duas vezes.
# A regra UNIQUE (session_id) impede que a mesma sessão esteja em dois itens de fatura ao mesmo tempo.
# (Recalcular uma fatura aberta não esbarra nisso: o recálculo apaga o item antigo antes de criar o novo.)
def test_sessao_nao_pode_ser_cobrada_duas_vezes(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    september = open_invoice(db, base.ana)
    september.items.append(item(september, session))
    db.flush()
    october = open_invoice(db, base.ana, period=at(1, 0, month=10).date())
    expect_integrity_error(db, lambda: october.items.append(item(october, session)), "uq_invoice_items_session")


# @pytest.mark.parametrize roda o mesmo teste uma vez para cada valor da lista: são 3 execuções, com
# status = suspensa, pendente e rejeitada. No relatório do pytest elas aparecem separadas, com o valor
# entre colchetes: test_sessao_nao_aprovada_nao_entra_na_fatura[suspended], [pending] e [rejected].
# Nas três, o gatilho recusa o item, porque só sessão aprovada ("approved") entra em fatura.
@pytest.mark.parametrize("status", [ValidationStatus.SUSPENDED, ValidationStatus.PENDING, ValidationStatus.REJECTED])
def test_sessao_nao_aprovada_nao_entra_na_fatura(db, base, status):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12), validation=status)
    invoice = open_invoice(db, base.ana)
    expect_integrity_error(db, lambda: invoice.items.append(item(invoice, session)), "precisa ser approved")


# O banco confere a conta de cada item: total = subtotal + imposto + overhead. O item tem subtotal 6,50,
# imposto 0 e overhead 0, mas diz que o total é 99,99: recusado (ck_items_total).
def test_aritmetica_da_linha_e_conferida_pelo_banco(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    invoice = open_invoice(db, base.ana)
    wrong_total = item(invoice, session, total=D("99.99"))
    expect_integrity_error(db, lambda: invoice.items.append(wrong_total), "ck_items_total")


# Falha do sistema nunca é cobrada. Um item com a regra "system_failure_no_charge" e total de 6,50 (o valor
# padrão do item de teste) é recusado: ck_items_failure_is_free exige total zero nessa regra.
def test_falha_do_sistema_nunca_tem_valor(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12), end_status="system_failure")
    invoice = open_invoice(db, base.ana)
    charged_failure = item(invoice, session, charge_rule="system_failure_no_charge")
    expect_integrity_error(db, lambda: invoice.items.append(charged_failure), "ck_items_failure_is_free")


# ---------------------------------------------------------------------------
# Regra 4 - fatura fechada é imutável
# ---------------------------------------------------------------------------
# Função de apoio (o nome não começa com test_, então o pytest não a roda como teste): monta uma fatura
# com um item de 6,50 e a fecha. Os totais da fatura são preenchidos à mão para baterem com o item, senão
# o banco nem deixaria fechar. Fechar pede as duas coisas juntas: status "closed" e a data de fechamento.
# "a, b = 1, x" atribui dois valores de uma vez; "a = b = c = valor" dá o mesmo valor a três campos.
def _closed_invoice(db, base) -> Invoice:
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    invoice = open_invoice(db, base.ana)
    invoice.items.append(item(invoice, session))
    invoice.sessions_count, invoice.grid_kwh = 1, session.grid_kwh
    invoice.grid_amount = invoice.subtotal = invoice.total = D("6.50")
    db.flush()
    invoice.status, invoice.closed_at = InvoiceStatus.CLOSED, at(1, 0, month=10)
    db.flush()
    return invoice


# Com a fatura fechada, nem um UPDATE direto no banco passa (text(...) é SQL escrito à mão, como faria
# alguém com acesso ao banco). O UPDATE zera total, subtotal e grid_amount juntos para a conta da fatura
# continuar coerente: a única coisa errada nele é mexer numa fatura fechada.
# ":i" é um parâmetro do SQL; o valor vem do dicionário {"i": invoice.id}.
def test_fatura_fechada_nao_pode_ser_alterada(db, base):
    invoice = _closed_invoice(db, base)
    expect_integrity_error(
        db,
        lambda: db.execute(
            text("UPDATE invoices SET total = 0, subtotal = 0, grid_amount = 0 WHERE id = :i"), {"i": invoice.id}
        ),
        "fechada",
    )


# Fatura fechada também não pode ser apagada.
def test_fatura_fechada_nao_pode_ser_apagada(db, base):
    invoice = _closed_invoice(db, base)
    expect_integrity_error(
        db, lambda: db.execute(text("DELETE FROM invoices WHERE id = :i"), {"i": invoice.id}), "fechada"
    )


# Os itens de uma fatura fechada também são intocáveis: não dá para alterar um item que já está lá
# (primeira parte) nem incluir um item novo, com outra recarga da Ana (segunda parte).
def test_itens_de_fatura_fechada_sao_imutaveis(db, base):
    invoice = _closed_invoice(db, base)
    expect_integrity_error(
        db,
        lambda: db.execute(
            text("UPDATE invoice_items SET calculation = '{}' WHERE invoice_id = :i"), {"i": invoice.id}
        ),
        "fatura fechada",
    )
    extra = charging_session(db, base, base.ana, at(22, 10), at(22, 12))
    expect_integrity_error(db, lambda: invoice.items.append(item(invoice, extra)), "fatura fechada")


# O banco só deixa fechar se os totais da fatura baterem com a soma dos itens. Aqui o item vale 6,50, mas
# os totais da fatura continuam zerados: o gatilho recusa o fechamento ("não conferem").
# close() é uma função criada dentro do teste porque um lambda não aceita atribuição (a = b).
def test_fatura_so_fecha_se_os_totais_baterem_com_os_itens(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    invoice = open_invoice(db, base.ana)
    invoice.items.append(item(invoice, session))
    db.flush()  # totais da fatura ainda zerados, item vale 6,50

    def close():
        invoice.status, invoice.closed_at = InvoiceStatus.CLOSED, at(1, 0, month=10)

    expect_integrity_error(db, close, "não conferem")


# A sessão estava aprovada quando entrou na fatura, mas depois uma anomalia foi registrada nela (como faria
# o detector da Frente 4), e o gatilho a suspendeu. Fechar a fatura agora seria cobrar uma sessão sob
# suspeita: o banco recusa ("deixaram de estar aprovadas"), e a fatura precisa ser recalculada antes.
def test_fatura_nao_fecha_com_sessao_que_deixou_de_estar_aprovada(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    invoice = open_invoice(db, base.ana)
    invoice.items.append(item(invoice, session))
    invoice.sessions_count, invoice.grid_kwh = 1, session.grid_kwh
    invoice.grid_amount = invoice.subtotal = invoice.total = D("6.50")
    db.flush()
    db.add(Anomaly(session_id=session.id, detector="lof", score=D("0.9")))  # suspende a sessão
    db.flush()

    def close():
        invoice.status, invoice.closed_at = InvoiceStatus.CLOSED, at(1, 0, month=10)

    expect_integrity_error(db, close, "deixaram de estar aprovadas")


# O período da fatura é sempre o dia 1 do mês (01/09 = setembro); dia 15 é recusado. A regra se chama
# ck_invoices_period_first_day, mas o match só precisa de um pedaço do nome.
def test_periodo_da_fatura_e_sempre_o_primeiro_dia_do_mes(db, base):
    expect_integrity_error(db, lambda: open_invoice(db, base.ana, period=at(15, 0).date()), "ck_invoices_period")


# ---------------------------------------------------------------------------
# Regra 5 - anomalia e auditoria
# ---------------------------------------------------------------------------
# Quando uma anomalia é registrada, o gatilho do banco faz duas coisas sozinho: suspende a sessão e grava
# o evento "anomaly_detected" na auditoria. db.refresh(session) relê a sessão do banco, porque quem mudou o
# status foi o gatilho, e o objeto no Python ainda guardava o valor antigo.
# .all() devolve a lista de eventos; o assert exige que seja exatamente um, o "anomaly_detected".
def test_deteccao_suspende_a_sessao_e_gera_auditoria(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    anomaly = Anomaly(session_id=session.id, detector="isolation_forest", score=D("0.8"))
    db.add(anomaly)
    db.flush()
    db.refresh(session)
    assert session.validation_status == ValidationStatus.SUSPENDED
    events = db.scalars(select(AuditEvent).where(AuditEvent.entity_id == str(anomaly.id))).all()
    assert [e.action for e in events] == ["anomaly_detected"]


# parametrize com dois nomes: cada par da lista vira uma execução do teste.
#   1ª execução: o síndico APROVA  -> a sessão volta a "approved".
#   2ª execução: o síndico REJEITA -> a sessão fica "rejected".
# Nas duas, o gatilho grava a auditoria com quem decidiu, o status antes e depois e a observação.
# A linha "anomaly.status, anomaly.reviewed_by, anomaly.reviewed_at = ..." preenche três campos de uma vez
# (a decisão, quem revisou e quando). .one() exige exatamente um evento de revisão: nem zero, nem dois.
@pytest.mark.parametrize(
    ("decision", "expected"),
    [(AnomalyStatus.APPROVED, ValidationStatus.APPROVED), (AnomalyStatus.REJECTED, ValidationStatus.REJECTED)],
)
def test_revisao_manual_grava_auditoria_e_atualiza_a_sessao(db, base, decision, expected):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    anomaly = Anomaly(session_id=session.id, detector="lof", score=D("0.9"))
    db.add(anomaly)
    db.flush()
    anomaly.status, anomaly.reviewed_by, anomaly.reviewed_at = decision, base.manager.id, at(22, 9)
    anomaly.review_note = "conferido com o morador"
    db.flush()
    db.refresh(session)
    assert session.validation_status == expected
    review = db.scalars(
        select(AuditEvent).where(AuditEvent.entity_id == str(anomaly.id), AuditEvent.action == "anomaly_review")
    ).one()
    assert review.actor_user_id == base.manager.id
    assert review.before_data["status"] == "pending_review"
    assert review.after_data["status"] == decision
    assert review.reason == "conferido com o morador"


# Mudar o status da anomalia sem dizer quem revisou e quando é recusado (ck_anomalies_review_fields):
# toda decisão humana precisa de responsável e data.
def test_revisao_sem_responsavel_e_recusada(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    anomaly = Anomaly(session_id=session.id, detector="lof")
    db.add(anomaly)
    db.flush()

    def review_without_reviewer():
        anomaly.status = AnomalyStatus.APPROVED

    expect_integrity_error(db, review_without_reviewer, "ck_anomalies_review_fields")


# A auditoria é "somente inserção": dá para gravar eventos novos, mas nunca alterar nem apagar os antigos,
# nem com SQL direto no banco.
def test_auditoria_e_somente_insercao(db, base):
    event = AuditEvent(entity_type="teste", entity_id="1", action="criado")
    db.add(event)
    db.flush()
    expect_integrity_error(
        db,
        lambda: db.execute(text("UPDATE audit_events SET action = 'apagado' WHERE id = :i"), {"i": event.id}),
        "somente inserção",
    )
    expect_integrity_error(
        db, lambda: db.execute(text("DELETE FROM audit_events WHERE id = :i"), {"i": event.id}), "somente inserção"
    )


# ---------------------------------------------------------------------------
# Regra 3 - tarifas versionadas
# ---------------------------------------------------------------------------
# A tarifa de teste vale de 01/09 em diante, sem data de fim. Uma nova a partir de 15/09, sem encerrar a
# anterior, faria duas tabelas valerem ao mesmo tempo: o banco recusa (ex_tariffs_no_overlap).
def test_duas_tarifas_nao_podem_valer_ao_mesmo_tempo(db, base):
    overlapping = Tariff(name="Nova", valid_from=at(15, 0), idle_fee_per_minute=D("0.3"))
    expect_integrity_error(db, lambda: db.add(overlapping), "ex_tariffs_no_overlap")


# O jeito certo de mudar preço: encerrar a tarifa atual (valid_to = 01/10) e criar a nova a partir de
# 01/10. Como o fim é exclusivo, 01/10 00:00 já é da nova: sem buraco e sem sobreposição.
# O select conta as tarifas gravadas (SELECT count(*) FROM tariffs): agora são duas.
def test_nova_versao_de_tarifa_apos_encerrar_a_anterior(db, base):
    base.tariff.valid_to = at(1, 0, month=10)
    db.flush()
    db.add(Tariff(name="Versão de outubro", valid_from=at(1, 0, month=10), idle_fee_per_minute=D("0.3")))
    db.flush()
    assert db.scalar(select(func.count()).select_from(Tariff)) == 2


# Apoio: usa a tarifa e o ISS de teste num item de fatura. A partir daí, os dois contam como "já faturados".
def _use_tariff_in_invoice(db, base):
    session = charging_session(db, base, base.ana, at(21, 10), at(21, 12))
    invoice = open_invoice(db, base.ana)
    invoice.items.append(item(invoice, session, tariff_id=base.tariff.id, tax_rule_ids=[base.tax.id]))
    db.flush()


# Tarifa já usada em fatura não muda; se mudasse, a fatura antiga não poderia mais ser refeita. Três
# tentativas, três recusas: mudar o preço de uma faixa, mudar a taxa de ociosidade e incluir uma janela
# nova (06h-07h). A mensagem do gatilho manda criar uma "nova versão" da tarifa.
def test_tarifa_ja_faturada_nao_pode_mudar_de_preco(db, base):
    _use_tariff_in_invoice(db, base)
    expect_integrity_error(
        db,
        lambda: db.execute(
            text("UPDATE tariff_bands SET grid_price_per_kwh = 9 WHERE tariff_id = :t"), {"t": base.tariff.id}
        ),
        "nova versão",
    )
    expect_integrity_error(
        db,
        lambda: db.execute(text("UPDATE tariffs SET idle_fee_per_minute = 9 WHERE id = :t"), {"t": base.tariff.id}),
        "nova versão",
    )
    expect_integrity_error(
        db,
        lambda: db.add(
            TariffWindow(tariff_id=base.tariff.id, band="peak", start_time=at(1, 6).time(), end_time=at(1, 7).time())
        ),
        "nova versão",
    )


# A única mudança permitida numa tarifa já faturada: encerrar a vigência (valid_to). Sem erro = passou.
def test_tarifa_ja_faturada_pode_ter_a_vigencia_encerrada(db, base):
    _use_tariff_in_invoice(db, base)
    db.execute(text("UPDATE tariffs SET valid_to = :v WHERE id = :t"), {"v": at(1, 0, month=10), "t": base.tariff.id})


# A mesma proteção vale para o imposto: a alíquota de um ISS já usado em fatura não muda.
def test_imposto_ja_faturado_nao_pode_mudar_de_aliquota(db, base):
    _use_tariff_in_invoice(db, base)
    expect_integrity_error(
        db,
        lambda: db.execute(text("UPDATE tax_rules SET rate_percent = 2 WHERE id = :t"), {"t": base.tax.id}),
        "nova versão",
    )


# A tarifa de teste já tem ponta das 18h às 21h e intermediário das 21h às 22h. Uma janela nova das 20h às
# 22h passaria por cima das duas: recusada (ex_tariff_windows_no_overlap). .time() pega só o horário.
def test_janelas_da_mesma_tarifa_nao_se_sobrepoem(db, base):
    window = TariffWindow(tariff_id=base.tariff.id, band="peak", start_time=at(1, 20).time(), end_time=at(1, 22).time())
    expect_integrity_error(db, lambda: db.add(window), "ex_tariff_windows_no_overlap")


# Uma janela de ponta numa tarifa que só tem preço fora de ponta: o motor não saberia quanto cobrar.
# A chave (tariff_id, band) exige que a faixa da janela tenha preço em tariff_bands (fk_tariff_windows_band).
# .replace(year=2025) troca só o ano da data.
def test_janela_so_usa_faixa_com_preco_definido(db, base):
    # vigência em 2025, antes da tarifa de teste, para não esbarrar na regra de sobreposição
    tariff = Tariff(
        name="Incompleta",
        valid_from=at(1, 0, month=1).replace(year=2025),
        valid_to=at(1, 0, month=2).replace(year=2025),
        idle_fee_per_minute=D("0.3"),
    )
    tariff.bands = [TariffBand(band="off_peak", green_price_per_kwh=D("0.3"), grid_price_per_kwh=D("0.6"))]
    tariff.windows = [TariffWindow(band="peak", start_time=at(1, 18).time(), end_time=at(1, 21).time())]
    expect_integrity_error(db, lambda: db.add(tariff), "fk_tariff_windows_band")

