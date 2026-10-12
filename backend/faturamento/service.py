## Serviço de faturamento: liga o motor de rateio ao banco de dados. ##

""" Funções que a Frente 2 (backend/API) pode expor como endpoints:

    generate_invoice(db, user_id, period)          -> POST /faturas/{periodo}/moradores/{id}
    generate_invoices_for_period(db, period)       -> POST /faturas/{periodo}/gerar
    close_invoice(db, invoice_id, actor_user_id)   -> POST /faturas/{id}/fechar
    review_anomaly(db, anomaly_id, decision, ...)  -> POST /anomalias/{id}/revisao
    (relatório de arrecadação em backend/faturamento/report.py)

Todas recebem uma sessão SQLAlchemy aberta; quem chama decide o commit.
"""

from __future__ import annotations

# UTC é o fuso "zero": os instantes (generated_at, closed_at, reviewed_at) são gravados nele.
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import config
from backend.db.enums import AnomalyStatus, InvoiceStatus, UserRole, ValidationStatus
from backend.db.models import Anomaly, AuditEvent, ChargingSession, Invoice, InvoiceItem, User

# As consultas ao banco ficam em repository.py; aqui o arquivo é chamado de "repo" (repo.tariff_at etc.).
from backend.faturamento import repository as repo
from backend.faturamento.mappers import session_to_input, tariff_to_spec, tax_rule_to_spec
from backend.faturamento.periods import first_day, month_bounds, period_label

# O motor de rateio: calcula uma sessão (calculate_session) e soma as sessões da fatura (summarize_invoice).
from backend.rateio.engine import ENGINE_VERSION, calculate_session, summarize_invoice
from backend.rateio.models import SessionCharge, SessionNotBillableError, TariffSpec
from backend.rateio.money import dec_str

# Texto que a fatura mostra para cada sessão que ficou de fora, conforme o status de validação dela.
UNBILLED_REASONS = {
    ValidationStatus.PENDING: "aguardando validação; entra na fatura quando for aprovada",
    ValidationStatus.SUSPENDED: "suspensa pelo detector de anomalias; aguarda revisão do síndico",
    ValidationStatus.REJECTED: "medição descartada na revisão de anomalia; não é cobrada",
}


# Erros próprios do faturamento. Com um tipo de erro para cada situação, a API (Frente 2) consegue
# responder com a mensagem certa em vez de um erro genérico.
class InvoiceClosedError(RuntimeError):
    """Tentativa de recalcular uma fatura fechada."""


class ReviewError(RuntimeError):
    """Revisão de anomalia inválida (decisão desconhecida, já revisada, revisor sem permissão)."""


# Grava um evento na trilha de auditoria: quem fez (actor_user_id), o quê (action), em qual registro
# (entity_type + entity_id), como estava antes (before), como ficou (after) e por quê (reason).
# O * na lista de parâmetros obriga a chamar pelo nome (entity_type="invoice", ...), para ninguém trocar
# a ordem dos argumentos sem perceber. No banco, a tabela de auditoria só aceita inserção (gatilho).
def record_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: object,
    action: str,
    actor_user_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=str(entity_id),  # guardado como texto, para servir para qualquer tabela
        action=action,
        before_data=before,
        after_data=after,
        reason=reason,
    )
    db.add(event)  # só agenda a gravação; o INSERT acontece no próximo flush ou commit
    return event


# GERACAO DA FARURA

def generate_invoice(
    db: Session,
    user_id: int,
    period: date,
    *,
    tz: ZoneInfo = config.CONDO_TIMEZONE,
    jurisdiction: str = config.TAX_JURISDICTION,
    actor_user_id: int | None = None,
) -> Invoice:
    #Gera (ou recalcula, se ainda aberta) a fatura mensal de um morador.

    # 1. Mês da fatura e seus limites (01/mês 00:00 até 01/mês seguinte 00:00, no fuso do condomínio).
    period = first_day(period)
    start, end = month_bounds(period, tz)
    # db.get busca pela chave primária (id) e devolve None se não existir.
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"Usuário {user_id} não existe")

    # 2. Procura a fatura deste morador neste mês. with_for_update() trava a linha até o fim da transação:
    #    se duas pessoas pedirem a mesma fatura ao mesmo tempo, a segunda espera a primeira terminar.
    invoice = db.scalars(
        select(Invoice).where(Invoice.user_id == user_id, Invoice.period == period).with_for_update()
    ).one_or_none()
    # Fatura fechada não muda: sessões novas vão para a fatura do mês seguinte.
    if invoice is not None and invoice.status == InvoiceStatus.CLOSED:
        raise InvoiceClosedError(
            f"Fatura {period_label(period)} do usuário {user_id} está fechada; "
            "novas sessões entram na fatura do mês seguinte"
        )
    if invoice is None:
        # Primeira vez: cria a fatura, ainda vazia.
        invoice = Invoice(user_id=user_id, period=period, engine_version=ENGINE_VERSION)
        db.add(invoice)
    else:
        invoice.items.clear()  
    db.flush()

    # 3. Preparação: os feriados, um "cache" de tarifas já convertidas e as listas que vão formar a fatura.
    holidays = repo.all_holidays(db)
    tariff_cache: dict[int, TariffSpec] = {}
    charges: list[SessionCharge] = []  # resultado do motor para cada sessão cobrada
    lines: list[dict[str, Any]] = []  # resumo de cada sessão, para a memória de cálculo da fatura
    not_included: list[dict[str, Any]] = []  # sessões que ficaram de fora, com o motivo

    # 4. Calcula cada sessão faturável do morador.
    for session in repo.billable_sessions(db, user_id, until=end):
        # A tarifa usada é a que valia no INÍCIO da sessão, e não a de hoje.
        tariff = repo.tariff_at(db, session.started_at)
        if tariff is None:
            not_included.append(_skip(session, tz, "sem tabela tarifária vigente no início da sessão"))
            continue  # pula para a próxima sessão
        # Converte cada tabela tarifária para o formato do motor uma vez só e reaproveita nas outras sessões.
        if tariff.id not in tariff_cache:
            tariff_cache[tariff.id] = tariff_to_spec(tariff)
        spec = tariff_cache[tariff.id]
        # Impostos que valiam no início da sessão, já convertidos para o formato do motor.
        taxes = [tax_rule_to_spec(r) for r in repo.tax_rules_at(db, session.started_at, jurisdiction)]
        # Se o motor recusar a sessão (ex.: energia fisicamente impossível), ela não é cobrada, aparece na
        # fatura como não incluída e o motivo fica registrado na auditoria.
        try:
            charge = calculate_session(session_to_input(session), spec, taxes, holidays, tz)
        except SessionNotBillableError as error:
            not_included.append(_skip(session, tz, str(error), error.code))
            record_audit(
                db,
                entity_type="charging_session",
                entity_id=session.id,
                action="session_not_billable",
                actor_user_id=actor_user_id,
                after={"code": error.code},
                reason=str(error),
            )
            continue

        # Sessão de mês anterior liberada só agora (ex.: anomalia aprovada): entra como lançamento posterior.
        is_late = session.started_at < start
        invoice.items.append(_to_item(session, charge, is_late))
        charges.append(charge)
        # Resumo da sessão para a memória de cálculo da fatura (horário no fuso do condomínio).
        lines.append(
            {
                "session_id": session.id,
                "started_at": session.started_at.astimezone(tz).isoformat(),
                "charge_rule": charge.charge_rule,
                "is_late_entry": is_late,
                "tariff_id": charge.tariff_id,
                "total": dec_str(charge.total, 2),
            }
        )

    # 5. Sessões do mês que ficam de fora (pendentes, suspensas ou rejeitadas), com o motivo para o morador.
    for unbilled in repo.unbilled_sessions(db, user_id, start, end):
        not_included.append(_skip(unbilled, tz, UNBILLED_REASONS[unbilled.validation_status]))

    # 6. Soma as sessões e copia cada total para a fatura. setattr(invoice, "total", x) é o mesmo que
    #    invoice.total = x, mas com o nome do campo numa variável: um "for" no lugar de 11 linhas.
    totals = summarize_invoice(charges)
    for attr in (
        "sessions_count",
        "green_kwh",
        "grid_kwh",
        "idle_minutes",
        "green_amount",
        "grid_amount",
        "idle_amount",
        "subtotal",
        "tax_amount",
        "overhead_amount",
        "total",
    ):
        setattr(invoice, attr, getattr(totals, attr))
    invoice.engine_version = ENGINE_VERSION  
    invoice.generated_at = datetime.now(UTC) 
    invoice.calculation = _invoice_calculation(user, period, start, end, totals, lines, not_included)
    db.flush()

    # 7. Registra na auditoria que a fatura foi gerada.
    record_audit(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_generated",
        actor_user_id=actor_user_id,
        after={
            "period": period_label(period),
            "user_id": user_id,
            "total": dec_str(invoice.total, 2),
            "sessions": invoice.sessions_count,
        },
    )
    return invoice


# Gera as faturas de todos no mês (o botão "gerar as faturas de setembro" do painel do síndico).
def generate_invoices_for_period(
    db: Session,
    period: date,
    *,
    tz: ZoneInfo = config.CONDO_TIMEZONE,
    jurisdiction: str = config.TAX_JURISDICTION,
    actor_user_id: int | None = None,
) -> list[Invoice]:
    #Gera as faturas do mês para todos os moradores ativos (inclusive fatura zero).
    # Aqui só interessa o fim do mês; o _ descarta o primeiro valor (o início).
    _, end = month_bounds(first_day(period), tz)
    invoices = []
    for user in repo.users_to_invoice(db, until=end):
        existing = db.scalars(
            select(Invoice).where(Invoice.user_id == user.id, Invoice.period == first_day(period))
        ).one_or_none()
        # Fatura já fechada não é recalculada: entra na lista do jeito que está.
        if existing is not None and existing.status == InvoiceStatus.CLOSED:
            invoices.append(existing)
            continue
        invoices.append(
            generate_invoice(db, user.id, period, tz=tz, jurisdiction=jurisdiction, actor_user_id=actor_user_id)
        )
    return invoices


def close_invoice(db: Session, invoice_id: int, actor_user_id: int | None = None) -> Invoice:
    """Fecha a fatura. A partir daqui o banco recusa qualquer alteração nela e nos seus itens."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ValueError(f"Fatura {invoice_id} não existe")
    # Fechar duas vezes não dá erro: devolve a fatura como está.
    if invoice.status == InvoiceStatus.CLOSED:
        return invoice
    _, period_end = month_bounds(invoice.period, config.CONDO_TIMEZONE)
    if datetime.now(UTC) < period_end:
        raise InvoiceClosedError(
            f"Fechamento disponível a partir de {period_end.strftime('%d/%m/%Y %H:%M')} (São Paulo)"
        )
    invoice.status = InvoiceStatus.CLOSED
    invoice.closed_at = datetime.now(UTC)
    # Se os totais não baterem com os itens, ou alguma sessão não estiver aprovada, o banco recusa o
    # fechamento e o erro aparece nesta linha.
    db.flush()  # o gatilho confere totais x itens e sessões aprovadas
    record_audit(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_closed",
        actor_user_id=actor_user_id,
        after={"total": dec_str(invoice.total, 2)},
    )
    return invoice



# REVISAO DE ANOMALIA

def review_anomaly(
    db: Session,
    anomaly_id: int,
    decision: str,
    reviewer_id: int,
    note: str | None = None,
) -> Anomaly:
   #Aprova (libera para cobrança) ou rejeita (não cobra) uma sessão suspeita.
    # Validações antes de mexer em qualquer coisa. Em {decision!r}, o !r mostra o valor entre aspas.
    if decision not in (AnomalyStatus.APPROVED, AnomalyStatus.REJECTED):
        raise ReviewError(f"Decisão inválida: {decision!r} (use 'approved' ou 'rejected')")
    # Só o gestor/síndico decide: é a revisão humana de um alerta automático.
    reviewer = db.get(User, reviewer_id)
    if reviewer is None or reviewer.role != UserRole.MANAGER:
        raise ReviewError("Somente o gestor/síndico pode revisar anomalias")
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise ReviewError(f"Anomalia {anomaly_id} não existe")
    # Cada anomalia só pode ser revisada uma vez.
    if anomaly.status != AnomalyStatus.PENDING_REVIEW:
        raise ReviewError(f"Anomalia {anomaly_id} já foi revisada ({anomaly.status})")

    # Registra a decisão: qual foi, quem decidiu, quando e a observação.
    anomaly.status = decision
    anomaly.reviewed_by = reviewer_id
    anomaly.reviewed_at = datetime.now(UTC)
    anomaly.review_note = note
    db.flush()  
    # Relê a sessão do banco, porque quem mudou o status dela foi o gatilho, e não o Python.
    db.refresh(anomaly.session)  
    return anomaly


#AUXILIARES

# Transforma o resultado do motor (SessionCharge) numa linha da tabela invoice_items.
def _to_item(session: ChargingSession, charge: SessionCharge, is_late: bool) -> InvoiceItem:
    return InvoiceItem(
        session_id=session.id,
        # Qual versão da tabela tarifária foi usada
        tariff_id=charge.tariff_id,  
        # Quais regras de imposto (a coluna guarda uma lista de ids)
        tax_rule_ids=list(charge.tax_rule_ids),  
        # Normal, sem ociosidade ou falha do sistema (valor zero)
        charge_rule=charge.charge_rule,  
        is_late_entry=is_late,
        green_kwh=charge.green_kwh,
        grid_kwh=charge.grid_kwh,
        idle_minutes=charge.idle_minutes,
        green_amount=charge.green_amount,
        grid_amount=charge.grid_amount,
        idle_amount=charge.idle_amount,
        subtotal=charge.subtotal,
        tax_amount=charge.tax_amount,
        overhead_amount=charge.overhead_amount,
        total=charge.total,
        calculation=charge.calculation,  
    )


# Uma entrada da lista "não incluídas" da fatura. O horário vai no fuso do condomínio, para o JSON sair
# igual em qualquer computador.
def _skip(session: ChargingSession, tz: ZoneInfo, reason: str, code: str | None = None) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "started_at": session.started_at.astimezone(tz).isoformat(),
        "validation_status": session.validation_status,
        "code": code,
        "reason": reason,
    }


# Monta a memória de cálculo da FATURA (a de cada sessão fica no item). É o JSON que o app do morador
# pode mostrar: fórmula, linhas, totais, sessões não incluídas e observações.
def _invoice_calculation(
    user: User,
    period: date,
    start: datetime,
    end: datetime,
    totals: Any,
    lines: list[dict[str, Any]],
    not_included: list[dict[str, Any]],
) -> dict[str, Any]:
    # Observações automáticas para dois casos que costumam gerar dúvida no morador.
    notes = []
    if totals.sessions_count == 0:
        notes.append("Fatura zero: nenhuma sessão faturável no período; não há cobrança mínima.")
    # any(...) responde "pelo menos uma linha é lançamento posterior?".
    if any(line["is_late_entry"] for line in lines):
        notes.append("Inclui sessão de mês anterior liberada após revisão, com a tarifa da sessão.")
    return {
        "engine_version": ENGINE_VERSION,
        "period": period_label(period),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "user": {"id": user.id, "name": user.name, "unit": user.unit.label if user.unit else None},
        "formula": "Total = soma, por sessão, de (Green + Grid + Ociosidade) + Imposto + Overhead",
        "lines": lines,
        "totals": {
            "sessions_count": totals.sessions_count,
            "green_kwh": dec_str(totals.green_kwh, 3),
            "grid_kwh": dec_str(totals.grid_kwh, 3),
            "idle_minutes": totals.idle_minutes,
            "green_amount": dec_str(totals.green_amount, 2),
            "grid_amount": dec_str(totals.grid_amount, 2),
            "idle_amount": dec_str(totals.idle_amount, 2),
            "subtotal": dec_str(totals.subtotal, 2),
            "tax_amount": dec_str(totals.tax_amount, 2),
            "overhead_amount": dec_str(totals.overhead_amount, 2),
            "total": dec_str(totals.total, 2),
        },
        "not_included": not_included,
        "notes": notes,
    }


def tariff_is_used(db: Session, tariff_id: int) -> bool:
   # Útil para o painel do síndico: tarifa já usada não pode ser editada, só versionada.
   # limit(1): basta achar um item para saber a resposta. db.scalar devolve o primeiro valor, ou None.
    return db.scalar(select(InvoiceItem.id).where(InvoiceItem.tariff_id == tariff_id))
