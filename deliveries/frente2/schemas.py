from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from decimal import Decimal
import datetime


class SessionDTO(BaseModel):
    """Contrato de sessao compartilhado por todas as frentes do grupo."""
    session_id: str
    charger_id: str
    card_id: str
    started_at: datetime.datetime
    ended_at: datetime.datetime
    total_kwh: float
    green_kwh: float
    grid_kwh: float
    average_power_kw: float
    max_power_kw: float
    # "failed" foi adicionado por nos (a regra "falha do sistema = R$0" precisa dele).
    # Pendente de confirmar com a Pessoa 1 e a Pessoa 4.
    status: Literal["completed", "failed"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----------------------------- Auth / cadastros -----------------------------

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8)
    unit_id: int


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    unit_id: int
    profile: str

    @classmethod
    def from_user(cls, u):
        return cls(id=u.id, name=u.name, email=u.email, unit_id=u.unit_id, profile=u.profile.value)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UnitCreate(BaseModel):
    unit: str = Field(min_length=1)


class UnitOut(ORMModel):
    id: int
    unit: str


class ChargerCreate(BaseModel):
    id: str = Field(min_length=1)


class ChargerOut(ORMModel):
    id: str


# ----------------------------- Reservas -----------------------------

class ReservationCreate(BaseModel):
    charger_id: str
    started_at: datetime.datetime
    ended_at: datetime.datetime


class ReservationOut(ORMModel):
    id: int
    user_id: int
    charger_id: str
    started_at: datetime.datetime
    ended_at: datetime.datetime
    status: str

    @classmethod
    def from_res(cls, r):
        return cls(id=r.id, user_id=r.user_id, charger_id=r.charger_id,
                   started_at=r.started_at, ended_at=r.ended_at, status=r.status.value)


# ----------------------------- Sessoes / anomalias -----------------------------

class IngestResult(BaseModel):
    session_id: str
    processing_status: str
    reservation_id: int | None
    user_id: int | None
    anomaly_id: int | None
    reasons: list[dict]


class SessionOut(BaseModel):
    session_id: str
    charger_id: str
    card_id: str
    started_at: datetime.datetime
    ended_at: datetime.datetime
    total_kwh: float
    green_kwh: float
    grid_kwh: float
    average_power_kw: float
    max_power_kw: float
    status: str
    processing_status: str
    reservation_id: int | None
    user_id: int | None

    @classmethod
    def from_session(cls, s):
        return cls(session_id=s.session_id, charger_id=s.charger_id, card_id=s.card_id,
                   started_at=s.started_at, ended_at=s.ended_at, total_kwh=s.total_kwh,
                   green_kwh=s.green_kwh, grid_kwh=s.grid_kwh, average_power_kw=s.average_power_kw,
                   max_power_kw=s.max_power_kw, status=s.status.value,
                   processing_status=s.processing_status.value,
                   reservation_id=s.reservation_id, user_id=s.user_id)


class AnomalyOut(BaseModel):
    id: int
    session_id: str
    layer_failed: int | None
    score: float | None
    reasons: list
    status: str
    reviewed_by: int | None
    reviewed_at: datetime.datetime | None

    @classmethod
    def from_anomaly(cls, a):
        return cls(id=a.id, session_id=a.session_id, layer_failed=a.layer_failed, score=a.score,
                   reasons=a.reasons, status=a.status.value, reviewed_by=a.reviewed_by,
                   reviewed_at=a.reviewed_at)


class ReviewIn(BaseModel):
    decision: Literal["approve", "reject"]
    # Obrigatorio para aprovar uma sessao que ainda nao tem morador (sessao orfa).
    user_id: int | None = None


# ----------------------------- Tarifas / faturas -----------------------------

class TariffCreate(BaseModel):
    name: str = Field(min_length=1)
    start_time: datetime.time
    end_time: datetime.time
    green_price: Decimal = Field(ge=0)
    grid_price: Decimal = Field(ge=0)
    valid_from: datetime.date
    valid_to: datetime.date | None = None


class TariffOut(ORMModel):
    id: int
    name: str
    start_time: datetime.time
    end_time: datetime.time
    green_price: Decimal
    grid_price: Decimal
    valid_from: datetime.date
    valid_to: datetime.date | None


class BillingConfigCreate(BaseModel):
    idle_fee_per_min: Decimal = Field(ge=0)
    idle_tolerance_min: int = Field(ge=0, default=15)
    tax_pct: Decimal = Field(ge=0)
    overhead_pct: Decimal = Field(ge=0)
    valid_from: datetime.date


class BillingConfigOut(ORMModel):
    id: int
    idle_fee_per_min: Decimal
    idle_tolerance_min: int
    tax_pct: Decimal
    overhead_pct: Decimal
    valid_from: datetime.date


class InvoiceGenerate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    user_id: int | None = None   # vazio = todos os moradores com sessoes aprovadas no mes


class InvoiceItemOut(ORMModel):
    id: int
    session_id: str
    green_cost: Decimal
    grid_cost: Decimal
    idle_cost: Decimal
    subtotal: Decimal
    tax: Decimal
    overhead: Decimal
    total: Decimal
    memory: dict


class InvoiceOut(BaseModel):
    id: int
    user_id: int
    year: int
    month: int
    status: str
    subtotal: Decimal
    tax: Decimal
    overhead: Decimal
    total: Decimal
    items: list[InvoiceItemOut] = []

    @classmethod
    def from_invoice(cls, inv, items):
        return cls(id=inv.id, user_id=inv.user_id, year=inv.year, month=inv.month,
                   status=inv.status.value, subtotal=inv.subtotal, tax=inv.tax,
                   overhead=inv.overhead, total=inv.total,
                   items=[InvoiceItemOut.model_validate(i) for i in items])
