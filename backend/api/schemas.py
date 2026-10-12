from datetime import date, time
from decimal import Decimal
from typing import Any, Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class DTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", allow_inf_nan=False)


class LoginIn(DTO):
    email: str
    password: str


class TokenOut(DTO):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = 28800


class UserCreate(DTO):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    password: str = Field(min_length=8, max_length=256)
    unit_id: int = Field(gt=0)


class UserOut(DTO):
    id: int
    name: str
    email: str
    role: Literal["resident", "manager"]
    unit_id: int | None
    active: bool
    reservation_blocked_until: AwareDatetime | None


class UnitCreate(DTO):
    block: str = Field(default="", max_length=100)
    number: str = Field(min_length=1, max_length=100)


class UnitOut(UnitCreate):
    id: int
    label: str


class ChargerCreate(DTO):
    code: str = Field(min_length=1, max_length=100)
    serial_number: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1)
    rated_power_kw: Decimal = Field(gt=0, le=99, decimal_places=2)
    connectors: int = Field(default=1, ge=1, le=10)
    location: str | None = None


class ChargerOut(ChargerCreate):
    id: int
    active: bool
    telemetry_status: Literal["unavailable"] = "unavailable"


class ReservationCreate(DTO):
    charger_id: int = Field(gt=0)
    connector: int = Field(default=1, ge=1)
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def interval(self):
        seconds = (self.ends_at - self.starts_at).total_seconds()
        if not 0 < seconds <= 12 * 3600:
            raise ValueError("Reserva deve durar entre 0 e 12 horas")
        return self


class ReservationOut(ReservationCreate):
    id: int
    user_id: int
    status: Literal["active", "in_use", "completed", "cancelled", "no_show"]


class BusyWindow(DTO):
    connector: int
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class AvailabilityOut(DTO):
    charger_id: int
    connectors: int
    busy: list[BusyWindow]


class PowerSample(DTO):
    measured_at: AwareDatetime
    power_kw: Decimal = Field(ge=0, decimal_places=3)
    green_power_kw: Decimal | None = Field(default=None, ge=0, decimal_places=3)


class SessionIn(DTO):
    source: Literal["simulator", "sems", "gateway"]
    session_id: str = Field(min_length=1, max_length=200)
    charger_id: str = Field(min_length=1, description="Código público do carregador, ex.: HCA01")
    connector: int = Field(default=1, ge=1)
    card_id: str | None = None
    started_at: AwareDatetime
    energy_ended_at: AwareDatetime | None = None
    ended_at: AwareDatetime
    total_kwh: Decimal = Field(ge=0, decimal_places=3)
    green_kwh: Decimal = Field(ge=0, decimal_places=3)
    grid_kwh: Decimal = Field(ge=0, decimal_places=3)
    average_power_kw: Decimal = Field(ge=0, decimal_places=2)
    max_power_kw: Decimal = Field(ge=0, decimal_places=2)
    status: Literal["completed", "user_stopped", "system_failure", "abnormal_disconnection"]
    failure_code: str | None = None
    power_samples: list[PowerSample] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def times(self):
        if self.ended_at <= self.started_at:
            raise ValueError("Fim deve ocorrer após o início da sessão")
        if self.energy_ended_at and not self.started_at <= self.energy_ended_at <= self.ended_at:
            raise ValueError("Fim da energia deve estar dentro da sessão")
        timestamps = [p.measured_at for p in self.power_samples]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("Medições duplicadas no mesmo instante")
        if any(not self.started_at <= t <= self.ended_at for t in timestamps):
            raise ValueError("Medição fora do intervalo da sessão")
        return self


class SessionOut(DTO):
    id: int
    source: str
    external_id: str
    charger_id: int
    connector: int
    card_id: str | None
    reservation_id: int | None
    user_id: int | None
    attribution_method: str
    started_at: AwareDatetime
    energy_ended_at: AwareDatetime | None
    ended_at: AwareDatetime | None
    total_kwh: Decimal
    green_kwh: Decimal
    grid_kwh: Decimal
    average_power_kw: Decimal | None
    max_power_kw: Decimal | None
    end_status: str
    validation_status: str


class DetectionOut(DTO):
    is_anomaly: bool
    layer: str
    score: float | None
    reasons: list[str]
    reasons_human: list[str]
    model_version: str | None


class IngestOut(DTO):
    session: SessionOut
    anomaly_id: int | None
    duplicate: bool
    detection: DetectionOut


class AnomalyOut(DTO):
    id: int
    session_id: int
    detected_at: AwareDatetime
    detector: str
    score: Decimal | None
    reasons: list[dict[str, Any]]
    status: str
    reviewed_by: int | None
    reviewed_at: AwareDatetime | None
    review_note: str | None


class ReviewIn(DTO):
    decision: Literal["approve", "reject"]
    user_id: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=2000)


class BandPriceIn(DTO):
    band: Literal["off_peak", "intermediate", "peak"]
    green_price_per_kwh: Decimal = Field(ge=0, decimal_places=4)
    grid_price_per_kwh: Decimal = Field(ge=0, decimal_places=4)


class WindowIn(DTO):
    band: Literal["intermediate", "peak"]
    start_time: time
    end_time: time


class TariffCreate(DTO):
    name: str = Field(min_length=1)
    valid_from: AwareDatetime
    idle_tolerance_minutes: int = Field(default=15, ge=0)
    idle_fee_per_minute: Decimal = Field(ge=0, decimal_places=4)
    overhead_percent: Decimal = Field(ge=0, le=100, decimal_places=2)
    weekends_holidays_off_peak: bool = True
    assembly_reference: str | None = None
    bands: list[BandPriceIn] = Field(min_length=1, max_length=3)
    windows: list[WindowIn] = Field(default_factory=list, max_length=8)


class TariffOut(TariffCreate):
    id: int
    valid_to: AwareDatetime | None


class TaxCreate(DTO):
    tax_type: Literal["iss", "icms", "ibs", "cbs"]
    jurisdiction: str = Field(min_length=1)
    rate_percent: Decimal = Field(ge=0, le=100, decimal_places=3)
    exclude_compensated_energy: bool = False
    legal_basis: str | None = None
    valid_from: AwareDatetime


class TaxOut(TaxCreate):
    id: int
    valid_to: AwareDatetime | None


class InvoiceGenerate(DTO):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    user_id: int | None = Field(default=None, gt=0)


class InvoiceItemOut(DTO):
    id: int
    session_id: int
    tariff_id: int | None
    charge_rule: str
    is_late_entry: bool
    green_kwh: Decimal
    grid_kwh: Decimal
    idle_minutes: int
    green_amount: Decimal
    grid_amount: Decimal
    idle_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    overhead_amount: Decimal
    total: Decimal
    calculation: dict[str, Any]


class InvoiceOut(DTO):
    id: int
    user_id: int
    period: date
    status: Literal["open", "closed"]
    sessions_count: int
    green_kwh: Decimal
    grid_kwh: Decimal
    idle_minutes: int
    green_amount: Decimal
    grid_amount: Decimal
    idle_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    overhead_amount: Decimal
    total: Decimal
    calculation: dict[str, Any]
    engine_version: str
    items: list[InvoiceItemOut]


class HealthOut(DTO):
    status: Literal["ok"]
    database: Literal["ok"]
    schema_version: str
    ai_model: str


class RecommendationOut(DTO):
    recommended_start: AwareDatetime
    recommended_end: AwareDatetime
    predicted_cost: Decimal
    cost_if_now: Decimal
    savings: Decimal
    model: Literal["baseline-deterministico"]
    assumptions: list[str]
