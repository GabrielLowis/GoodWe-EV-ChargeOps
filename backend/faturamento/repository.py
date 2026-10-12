"""Consultas usadas pelo faturamento (tarifa vigente, sessões faturáveis etc.)."""

from __future__ import annotations

from datetime import date, datetime

# Peças para montar as consultas: select (SELECT), or_ (OR) e exists (EXISTS).
from sqlalchemy import exists, or_, select

# Session: a conversa com o banco. selectinload: carrega junto os objetos ligados (ver tariff_at).
from sqlalchemy.orm import Session, selectinload

from backend.db.enums import SessionEndStatus, UserRole, ValidationStatus
from backend.db.models import ChargingSession, Holiday, InvoiceItem, Tariff, TaxRule, User


# Qual versão da tabela tarifária valia num instante (ex.: no início de uma recarga).
def tariff_at(db: Session, instant: datetime) -> Tariff | None:
    """Versão da tabela tarifária vigente no instante (validade temporal)."""
    stmt = (
        select(Tariff)
        # Vigente = começou até o instante E (não tem data de fim OU termina depois do instante).
        .where(Tariff.valid_from <= instant, or_(Tariff.valid_to.is_(None), Tariff.valid_to > instant))
        # Traz as faixas e as janelas da tarifa nesta mesma busca. Sem isso, cada acesso a tariff.bands
        # faria mais uma consulta ao banco.
        .options(selectinload(Tariff.bands), selectinload(Tariff.windows))
    )
    # one_or_none: devolve a tarifa, ou None se não houver nenhuma. Nunca haverá duas, porque o banco
    # recusa tarifas com vigências sobrepostas (restrição EXCLUDE da migration).
    return db.scalars(stmt).one_or_none()


# Impostos que valiam num instante, na jurisdição do condomínio (ex.: "BR-SP-SAO_PAULO").
def tax_rules_at(db: Session, instant: datetime, jurisdiction: str) -> list[TaxRule]:
    """Impostos vigentes na jurisdição (mais de um tipo pode valer na transição IBS/CBS)."""
    stmt = (
        select(TaxRule)
        .where(
            TaxRule.jurisdiction == jurisdiction,
            # Mesma regra de vigência da tarifa.
            TaxRule.valid_from <= instant,
            or_(TaxRule.valid_to.is_(None), TaxRule.valid_to > instant),
        )
        # Ordem fixa (por tipo de imposto), para a memória de cálculo sair sempre igual.
        .order_by(TaxRule.tax_type)
    )
    # Pode valer mais de um imposto ao mesmo tempo, então devolve uma lista.
    return list(db.scalars(stmt))


# Todas as datas de feriado cadastradas. frozenset é um conjunto que não pode ser alterado, e perguntar
# "esta data é feriado?" a um conjunto é instantâneo.
def all_holidays(db: Session) -> frozenset[date]:
    return frozenset(db.scalars(select(Holiday.holiday_date)))


# Condição usada em duas consultas: "a sessão ainda não aparece em nenhum item de fatura".
# Em SQL: NOT EXISTS (SELECT id FROM invoice_items WHERE invoice_items.session_id = charging_sessions.id).
# O ~ na frente é o NOT. O _ no nome indica uso interno deste arquivo.
def _not_invoiced():
    return ~exists(select(InvoiceItem.id).where(InvoiceItem.session_id == ChargingSession.id))


# Sessões que podem entrar agora na fatura do morador.
def billable_sessions(db: Session, user_id: int, until: datetime) -> list[ChargingSession]:
    #Sessões aprovadas, encerradas e ainda não faturadas do morador, iniciadas antes de `until`.
    stmt = (
        select(ChargingSession)
        .where(
            ChargingSession.user_id == user_id,  # do morador
            ChargingSession.validation_status == ValidationStatus.APPROVED,  # aprovada
            ChargingSession.end_status != SessionEndStatus.IN_PROGRESS,  # já terminou
            ChargingSession.started_at < until,  # começou antes do fim do mês da fatura
            _not_invoiced(),  # e ainda não foi cobrada em nenhuma fatura
        )
        .order_by(ChargingSession.started_at)  # em ordem de data, como aparecem na fatura
        # Traz junto a curva de potência e o carregador, que o mappers.py vai usar.
        .options(selectinload(ChargingSession.samples), selectinload(ChargingSession.charger))
    )
    return list(db.scalars(stmt))


# Sessões do mês que ficam de fora da fatura, para a fatura explicar o motivo ao morador.
def unbilled_sessions(db: Session, user_id: int, start: datetime, end: datetime) -> list[ChargingSession]:
   #Sessões do morador no período que não entram na fatura: pendentes, suspensas ou rejeitadas.
    stmt = (
        select(ChargingSession)
        .where(
            ChargingSession.user_id == user_id,
            # Iniciadas dentro do mês (o início conta, o fim não).
            ChargingSession.started_at >= start,
            ChargingSession.started_at < end,
            # .in_([...]): o status é um destes três.
            ChargingSession.validation_status.in_(
                [ValidationStatus.PENDING, ValidationStatus.SUSPENDED, ValidationStatus.REJECTED]
            ),
        )
        .order_by(ChargingSession.started_at)
    )
    return list(db.scalars(stmt))


# Quem recebe fatura no mês.
def users_to_invoice(db: Session, until: datetime) -> list[User]:
    # Moradores ativos (recebem fatura, mesmo que zero) e qualquer usuário com sessão faturável.
    # Subconsulta "este usuário tem alguma sessão faturável?", com as mesmas condições de billable_sessions.
    has_billable = exists(
        select(ChargingSession.id).where(
            ChargingSession.user_id == User.id,
            ChargingSession.validation_status == ValidationStatus.APPROVED,
            ChargingSession.end_status != SessionEndStatus.IN_PROGRESS,
            ChargingSession.started_at < until,
            _not_invoiced(),
        )
    )
    # Morador ativo OU usuário com sessão faturável. Dentro de uma consulta, o E se escreve com & (o "and" do Python não funciona aqui).
    stmt = select(User).where(or_((User.role == UserRole.RESIDENT) & User.active, has_billable)).order_by(User.id)
    return list(db.scalars(stmt))

