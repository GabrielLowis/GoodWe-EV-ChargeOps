## Fábricas de dados mínimos para os testes de integração do banco. ##

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
# "as D" dá um apelido curto: D("0.30") é o mesmo que Decimal("0.30").
from decimal import Decimal as D

import pytest
# IntegrityError: o erro que chega ao Python quando o PostgreSQL recusa um dado por uma regra de
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db.enums import AttributionMethod, Band, ReservationStatus, SessionEndStatus, UserRole, ValidationStatus
from backend.db.models import (
    Charger,
    ChargingSession,
    CondoUnit,
    Invoice,
    InvoiceItem,
    Reservation,
    Tariff,
    TariffBand,
    TariffWindow,
    TaxRule,
    User,
)
from backend.rateio.engine import ENGINE_VERSION
from backend.tests.helpers import at

# Agrupa o cadastro mínimo criado por build_base, para os testes escreverem base.ana, base.charger etc.
@dataclass
class BaseData:
    manager: User
    ana: User
    bruno: User
    charger: Charger  # 1 conector
    charger2: Charger  # 2 conectores
    tariff: Tariff
    tax: TaxRule


# O cadastro mínimo que quase todo teste de banco usa:
# - uma unidade (T-1) com dois moradores, Ana e Bruno, e uma síndica;
# - dois carregadores: T1 (7 kW, 1 conector) e T2 (22 kW, 2 conectores);
# - uma tarifa com os preços da demonstração, valendo a partir de 01/09/2026 e sem data de fim;
# - o ISS de 5%, valendo desde 01/01/2026.
# db.add_all põe tudo na fila e db.flush() grava: os objetos ganham id.
def build_base(db: Session) -> BaseData:
    unit = CondoUnit(block="T", number="1")
    manager = User(name="Síndica Teste", email="sindica@teste.dev", role=UserRole.MANAGER)
    ana = User(name="Ana Teste", email="ana@teste.dev", role=UserRole.RESIDENT, unit=unit)
    bruno = User(name="Bruno Teste", email="bruno@teste.dev", role=UserRole.RESIDENT, unit=unit)
    charger = Charger(code="T1", serial_number="SN-T1", model="GW7K-HCA-20", rated_power_kw=D("7"), connectors=1)
    charger2 = Charger(code="T2", serial_number="SN-T2", model="GW22K-HCA-20", rated_power_kw=D("22"), connectors=2)
    tariff = Tariff(name="Tarifa teste", valid_from=at(1, 0), idle_fee_per_minute=D("0.25"), overhead_percent=D("5"))
    # Preço (Green, Grid) de cada faixa, os mesmos da versão 2 da demonstração.
    tariff.bands = [
        TariffBand(band=Band.OFF_PEAK, green_price_per_kwh=D("0.30"), grid_price_per_kwh=D("0.65")),
        TariffBand(band=Band.INTERMEDIATE, green_price_per_kwh=D("0.30"), grid_price_per_kwh=D("0.95")),
        TariffBand(band=Band.PEAK, green_price_per_kwh=D("0.30"), grid_price_per_kwh=D("1.45")),
    ]
    
    # Janelas de dia útil: time(17) é 17:00. Fora delas, vale o preço fora de ponta.
    tariff.windows = [
        TariffWindow(band=Band.INTERMEDIATE, start_time=time(17), end_time=time(18)),
        TariffWindow(band=Band.PEAK, start_time=time(18), end_time=time(21)),
        TariffWindow(band=Band.INTERMEDIATE, start_time=time(21), end_time=time(22)),
    ]
    tax = TaxRule(tax_type="iss", jurisdiction="BR-SP-SAO_PAULO", rate_percent=D("5"), valid_from=at(1, 0, month=1))
    db.add_all([unit, manager, ana, bruno, charger, charger2, tariff, tax])
    db.flush()
    return BaseData(manager, ana, bruno, charger, charger2, tariff, tax)

# Cria e grava uma reserva. Sem dizer nada, ela usa o conector 1 e fica com o status "ativa".
def reserve(
    db: Session,
    user: User,
    charger: Charger,
    start: datetime,
    end: datetime,
    connector: int = 1,
    status: str = ReservationStatus.ACTIVE,
) -> Reservation:
    reservation = Reservation(
        user_id=user.id, charger_id=charger.id, connector=connector, starts_at=start, ends_at=end, status=status
    )
    db.add(reservation)
    db.flush()
    return reservation

# Cria e grava uma recarga já encerrada e aprovada, com toda a energia como Grid (da rede).
# - Com morador: cria antes uma reserva dele no mesmo horário (já concluída) e atribui a recarga por essa
#   reserva, como o sistema faz. Sem morador (user=None): a recarga fica "não atribuída".
# - O * na lista de parâmetros obriga a passar os seguintes pelo nome: charging_session(..., kwh="5").
# - "charger or base.charger": se o teste não escolher o carregador, usa o T1.
# - external_id é o código da recarga na fonte de dados. Sem um informado, monta um com o horário de
#   início (ex.: "simulator-2026-09-21T10:00:00-03:00"), para não repetir entre as recargas do teste.
def charging_session(
    db: Session,
    base: BaseData,
    user: User | None,
    start: datetime,
    end: datetime,
    *,
    charger: Charger | None = None,
    kwh: str = "10",
    source: str = "simulator",
    external_id: str | None = None,
    validation: str = ValidationStatus.APPROVED,
    end_status: str = SessionEndStatus.COMPLETED,
) -> ChargingSession:
    charger = charger or base.charger
    reservation = None
    if user is not None:
        reservation = reserve(db, user, charger, start, end, status=ReservationStatus.COMPLETED)
    session = ChargingSession(
        source=source,
        external_id=external_id or f"{source}-{start.isoformat()}",
        charger_id=charger.id,
        user_id=user.id if user else None,
        reservation_id=reservation.id if reservation else None,
        attribution_method=AttributionMethod.RESERVATION if user else AttributionMethod.UNATTRIBUTED,
        started_at=start,
        energy_ended_at=end,
        ended_at=end,
        total_kwh=D(kwh),
        grid_kwh=D(kwh),
        end_status=end_status,
        validation_status=validation,
    )
    db.add(session)
    db.flush()
    return session

# Cria e grava uma fatura aberta, ainda vazia. Sem período informado, usa setembro/2026:
# at(1, 0).date() é 01/09/2026 (o período de uma fatura é sempre o dia 1 do mês).
def open_invoice(db: Session, user: User, period=None) -> Invoice:
    invoice = Invoice(user_id=user.id, period=period or at(1, 0).date(), engine_version=ENGINE_VERSION)
    db.add(invoice)
    db.flush()
    return invoice

# Monta (sem gravar) um item de fatura simples: tudo como energia da rede, sem imposto e sem overhead,
# então subtotal = total = amount. **overrides troca qualquer campo, ex.: item(..., total=D("99.99")).
# O parâmetro invoice não é usado aqui dentro: quem liga o item à fatura é o teste, com
# invoice.items.append(item(invoice, session)). Quando o item é gravado, o SQLAlchemy copia sozinho o id e o
# user_id da fatura para o item (é assim que a relação items foi declarada em backend/db/models.py).
def item(invoice: Invoice, session: ChargingSession, amount: str = "6.50", **overrides) -> InvoiceItem:
    """Item simples: tudo como energia da rede, sem imposto e overhead."""
    data = dict(
        session_id=session.id,
        charge_rule="normal",
        green_kwh=D("0"),
        grid_kwh=session.grid_kwh,
        idle_minutes=0,
        green_amount=D("0"),
        grid_amount=D(amount),
        idle_amount=D("0"),
        subtotal=D(amount),
        tax_amount=D("0"),
        overhead_amount=D("0"),
        total=D(amount),
        calculation={},
    )
    data.update(overrides)
    return InvoiceItem(**data)

# A peça central dos testes de integridade: executa uma ação e EXIGE que o banco a recuse.
# - action é uma função sem parâmetros, quase sempre um lambda: lambda: reserve(db, ...). O lambda
#   embrulha a ação para ela rodar só aqui dentro, na hora certa. Se o teste chamasse reserve(...) direto,
#   o erro estouraria antes de chegar a este "with", e o teste quebraria em vez de passar.
# - pytest.raises(IntegrityError, match=...) só deixa o teste passar se acontecer um IntegrityError cuja
#   mensagem contenha o texto de match (ex.: o nome da regra, "ex_reservations_no_overlap"). Se o banco
#   aceitar a ação, ou recusar por outro motivo, o teste falha.
# - db.begin_nested() abre um savepoint: quando o erro acontece, só a ação recusada é desfeita. O que o
#   teste gravou antes continua lá, e ele pode seguir com outras verificações.
# - db.flush() envia na hora o que estiver na fila, para o erro aparecer já nesta linha.
# - Devolve o erro, caso o teste queira examiná-lo.
def expect_integrity_error(db: Session, action, match: str | None = None) -> IntegrityError:
    """Executa `action` num savepoint e exige que o banco recuse (o teste continua depois)."""
    with pytest.raises(IntegrityError, match=match) as error, db.begin_nested():
        action()
        db.flush()
    return error.value
