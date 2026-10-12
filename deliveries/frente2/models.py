from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from database import engine
from enum import Enum
from decimal import Decimal
from sqlalchemy import ForeignKey, JSON, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
import datetime

# JSONB no PostgreSQL (memoria de calculo), JSON comum em outros bancos (testes com SQLite).
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


# ----------------------------- Enums -----------------------------

class ProfileUser(Enum):
    Gestor = "Gestor"
    Morador = "Morador"


class ReservationStatus(Enum):
    Await = "Await"
    Completed = "Completed"
    Cancelled = "Cancelled"
    No_show = "No Show"


class ChargingStatus(Enum):
    # O NOME do membro e o que o SessionDTO envia ("completed", "failed").
    completed = "Completed"
    failed = "Failed"


class ProcessingStatus(Enum):
    """Em que ponto do pipeline a sessao esta (separado do status que vem do carregador)."""
    Received = "Received"      # acabou de chegar
    Orphan = "Orphan"          # sem reserva: aguarda decisao do sindico
    Suspended = "Suspended"    # barrada pela validacao/IA: aguarda o sindico
    Approved = "Approved"      # liberada para o rateio
    Rejected = "Rejected"      # rejeitada pelo sindico (nao e cobrada)
    Billed = "Billed"          # ja entrou em uma fatura


class AnomalyStatus(Enum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"


class InvoiceStatus(Enum):
    Open = "Open"
    Closed = "Closed"


# ----------------------------- Nucleo -----------------------------

class CondoUnit(Base):
    __tablename__ = "condo_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit: Mapped[str]


class Charger(Base):
    __tablename__ = "chargers"
    id: Mapped[str] = mapped_column(primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    unit_id: Mapped[int] = mapped_column(ForeignKey("condo_units.id"))
    profile: Mapped[ProfileUser]
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]


class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    charger_id: Mapped[str] = mapped_column(ForeignKey("chargers.id"))
    started_at: Mapped[datetime.datetime]
    ended_at: Mapped[datetime.datetime]
    status: Mapped[ReservationStatus]


class ChargingSession(Base):
    __tablename__ = "charging_sessions"
    session_id: Mapped[str] = mapped_column(primary_key=True)
    reservation_id: Mapped[int | None] = mapped_column(ForeignKey("reservations.id"))
    # Morador dono da sessao: vem da reserva, ou e definido pelo sindico (sessao orfa).
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    charger_id: Mapped[str] = mapped_column(ForeignKey("chargers.id"))
    card_id: Mapped[str]
    started_at: Mapped[datetime.datetime]
    ended_at: Mapped[datetime.datetime]
    total_kwh: Mapped[float]
    green_kwh: Mapped[float]
    grid_kwh: Mapped[float]
    average_power_kw: Mapped[float]
    max_power_kw: Mapped[float]
    status: Mapped[ChargingStatus]
    processing_status: Mapped[ProcessingStatus] = mapped_column(default=ProcessingStatus.Received)


# ----------------------------- Tarifas e faturas -----------------------------

class Tariff(Base):
    """Uma faixa tarifaria. Versionada por validade: a mesma faixa (name) pode ter varias linhas."""
    __tablename__ = "tariffs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    start_time: Mapped[datetime.time]
    end_time: Mapped[datetime.time]
    green_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    grid_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    valid_from: Mapped[datetime.date]
    valid_to: Mapped[datetime.date | None]


class BillingConfig(Base):
    """Parametros de cobranca (ociosidade, imposto, overhead), tambem versionados por validade."""
    __tablename__ = "billing_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    idle_fee_per_min: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    idle_tolerance_min: Mapped[int]
    tax_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    overhead_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    valid_from: Mapped[datetime.date]


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("user_id", "year", "month", name="uq_invoice_user_month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    year: Mapped[int]
    month: Mapped[int]
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.Open)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    overhead: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    # unique=True: uma sessao nunca e cobrada duas vezes.
    session_id: Mapped[str] = mapped_column(ForeignKey("charging_sessions.session_id"), unique=True)
    green_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    grid_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    idle_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    overhead: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # Memoria de calculo: tudo que e preciso para reproduzir o valor (JSONB no PostgreSQL).
    memory: Mapped[dict] = mapped_column(JSON_TYPE)


# ----------------------------- Anomalias e auditoria -----------------------------

class Anomaly(Base):
    __tablename__ = "anomalies"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("charging_sessions.session_id"))
    layer_failed: Mapped[int | None]
    score: Mapped[float | None]
    reasons: Mapped[list] = mapped_column(JSON_TYPE)
    status: Mapped[AnomalyStatus] = mapped_column(default=AnomalyStatus.Pending)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime.datetime | None]
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str]
    entity: Mapped[str]
    entity_id: Mapped[str]
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    details: Mapped[dict] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
