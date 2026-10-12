import datetime
from decimal import Decimal
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from models import (ChargingSession, ChargingStatus, ProcessingStatus, Tariff, BillingConfig,
                    Invoice, InvoiceItem, InvoiceStatus)
from services import audit
from services.rateio import Band, Config, calculate_charge


class BillingError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def active_bands(db: Session, day: datetime.date) -> list[Band]:
    """Faixas vigentes no dia. Se a mesma faixa tem varias versoes, vale a mais recente."""
    rows = db.scalars(select(Tariff).where(
        Tariff.valid_from <= day, or_(Tariff.valid_to.is_(None), Tariff.valid_to >= day))).all()
    latest: dict[str, Tariff] = {}
    for t in rows:
        if t.name not in latest or t.valid_from > latest[t.name].valid_from:
            latest[t.name] = t
    return [Band(t.name, t.start_time, t.end_time, t.green_price, t.grid_price) for t in latest.values()]


def active_config(db: Session, day: datetime.date) -> Config | None:
    row = db.scalars(select(BillingConfig).where(BillingConfig.valid_from <= day)
                     .order_by(BillingConfig.valid_from.desc())).first()
    if row is None:
        return None
    return Config(row.idle_fee_per_min, row.idle_tolerance_min, row.tax_pct, row.overhead_pct)


def month_range(year: int, month: int):
    first = datetime.datetime(year, month, 1)
    nxt = datetime.datetime(year + (month == 12), (month % 12) + 1, 1)
    return first, nxt


def generate_invoice(db: Session, user_id: int, year: int, month: int) -> Invoice | None:
    invoice = db.scalar(select(Invoice).where(Invoice.user_id == user_id, Invoice.year == year,
                                              Invoice.month == month))

    first, nxt = month_range(year, month)
    sessions = db.scalars(select(ChargingSession).where(
        ChargingSession.user_id == user_id,
        ChargingSession.processing_status == ProcessingStatus.Approved,
        ChargingSession.started_at >= first, ChargingSession.started_at < nxt,
    ).order_by(ChargingSession.started_at)).all()

    # Fatura fechada nunca muda: se ha sessao nova para cobrar nela, recusa; senao devolve como esta.
    if invoice is not None and invoice.status == InvoiceStatus.Closed:
        if sessions:
            raise BillingError(409, "Fatura fechada nao pode ser alterada")
        return invoice

    if invoice is None and not sessions:
        return None
    if invoice is None:
        invoice = Invoice(user_id=user_id, year=year, month=month)
        db.add(invoice)
        db.flush()

    for s in sessions:
        day = s.started_at.date()
        bands = active_bands(db, day)
        config = active_config(db, day)
        if not bands or config is None:
            raise BillingError(422, f"Configure as tarifas e a cobranca vigentes em {day} antes de faturar")
        try:
            calc = calculate_charge(
                started_at=s.started_at, ended_at=s.ended_at, total_kwh=s.total_kwh,
                green_kwh=s.green_kwh, grid_kwh=s.grid_kwh, max_power_kw=s.max_power_kw,
                failed=(s.status == ChargingStatus.failed), bands=bands, config=config)
        except ValueError as e:
            raise BillingError(422, str(e))
        calc["memory"]["session_id"] = s.session_id
        db.add(InvoiceItem(invoice_id=invoice.id, session_id=s.session_id,
                           green_cost=calc["green_cost"], grid_cost=calc["grid_cost"],
                           idle_cost=calc["idle_cost"], subtotal=calc["subtotal"], tax=calc["tax"],
                           overhead=calc["overhead"], total=calc["total"], memory=calc["memory"]))
        s.processing_status = ProcessingStatus.Billed
    db.flush()

    totals = db.execute(select(
        func.coalesce(func.sum(InvoiceItem.subtotal), 0), func.coalesce(func.sum(InvoiceItem.tax), 0),
        func.coalesce(func.sum(InvoiceItem.overhead), 0), func.coalesce(func.sum(InvoiceItem.total), 0),
    ).where(InvoiceItem.invoice_id == invoice.id)).one()
    invoice.subtotal, invoice.tax, invoice.overhead, invoice.total = (Decimal(str(v)) for v in totals)

    audit.record(db, "INVOICE_GENERATED", "invoice", invoice.id, user_id,
                 {"year": year, "month": month, "new_sessions": len(sessions), "total": str(invoice.total)})
    db.commit()
    return invoice
