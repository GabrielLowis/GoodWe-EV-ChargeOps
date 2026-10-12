from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import (Tariff, BillingConfig, Invoice, InvoiceItem, InvoiceStatus, User, ProfileUser,
                    ChargingSession, ProcessingStatus)
from schemas import (TariffCreate, TariffOut, BillingConfigCreate, BillingConfigOut,
                     InvoiceGenerate, InvoiceOut)
from security import get_current_user, require_manager
from services import audit
from services.billing import generate_invoice, BillingError, month_range

router = APIRouter(tags=["Tarifas, faturas e financeiro"])


# ----- tarifas e parametros de cobranca (somente gestor) -----

@router.post("/tarifas", response_model=TariffOut, status_code=201)
def create_tariff(body: TariffCreate, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    tariff = Tariff(**body.model_dump())
    db.add(tariff)
    db.flush()
    audit.record(db, "TARIFF_CREATED", "tariff", tariff.id, manager.id, {"name": tariff.name})
    db.commit()
    return tariff


@router.get("/tarifas", response_model=list[TariffOut])
def list_tariffs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Tariff).order_by(Tariff.valid_from.desc(), Tariff.start_time)).all()


@router.post("/configuracao-cobranca", response_model=BillingConfigOut, status_code=201)
def create_config(body: BillingConfigCreate, db: Session = Depends(get_db),
                  manager: User = Depends(require_manager)):
    config = BillingConfig(**body.model_dump())
    db.add(config)
    db.flush()
    audit.record(db, "BILLING_CONFIG_CREATED", "billing_config", config.id, manager.id)
    db.commit()
    return config


@router.get("/configuracao-cobranca", response_model=list[BillingConfigOut])
def list_configs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(BillingConfig).order_by(BillingConfig.valid_from.desc())).all()


# ----- faturas -----

def _full(db: Session, invoice: Invoice) -> InvoiceOut:
    items = db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
                       .order_by(InvoiceItem.id)).all()
    return InvoiceOut.from_invoice(invoice, items)


@router.post("/faturas/gerar", response_model=list[InvoiceOut])
def generate(body: InvoiceGenerate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    first, nxt = month_range(body.year, body.month)
    if body.user_id is not None:
        user_ids = [body.user_id]
    else:
        with_sessions = db.scalars(select(ChargingSession.user_id).where(
            ChargingSession.user_id.is_not(None),
            ChargingSession.processing_status == ProcessingStatus.Approved,
            ChargingSession.started_at >= first, ChargingSession.started_at < nxt).distinct()).all()
        with_invoice = db.scalars(select(Invoice.user_id).where(
            Invoice.year == body.year, Invoice.month == body.month)).all()
        user_ids = sorted(set(with_sessions) | set(with_invoice))
    invoices = []
    try:
        for uid in user_ids:
            invoice = generate_invoice(db, uid, body.year, body.month)
            if invoice is not None:
                invoices.append(_full(db, invoice))
    except BillingError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.detail)
    if body.user_id is not None and not invoices:
        raise HTTPException(404, "Nenhuma sessao aprovada para faturar neste mes")
    return invoices


@router.get("/faturas", response_model=list[InvoiceOut])
def list_invoices(user_id: int | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    stmt = select(Invoice).order_by(Invoice.year.desc(), Invoice.month.desc())
    if user.profile != ProfileUser.Gestor:
        stmt = stmt.where(Invoice.user_id == user.id)
    elif user_id is not None:
        stmt = stmt.where(Invoice.user_id == user_id)
    return [_full(db, i) for i in db.scalars(stmt).all()]


@router.get("/faturas/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or (user.profile != ProfileUser.Gestor and invoice.user_id != user.id):
        raise HTTPException(404, "Fatura nao encontrada")
    return _full(db, invoice)


@router.post("/faturas/{invoice_id}/fechar", response_model=InvoiceOut)
def close_invoice(invoice_id: int, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Fatura nao encontrada")
    if invoice.status == InvoiceStatus.Closed:
        raise HTTPException(409, "Fatura ja fechada")
    invoice.status = InvoiceStatus.Closed
    audit.record(db, "INVOICE_CLOSED", "invoice", invoice.id, manager.id, {"total": str(invoice.total)})
    db.commit()
    return _full(db, invoice)


@router.get("/relatorios/arrecadacao")
def collection_report(year: int, month: int, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    """Relatorio mensal de arrecadacao para o fechamento com o condominio."""
    rows = db.execute(select(Invoice.status, func.count(Invoice.id), func.coalesce(func.sum(Invoice.total), 0))
                      .where(Invoice.year == year, Invoice.month == month).group_by(Invoice.status)).all()
    by_status = {s.value: {"invoices": int(n), "total": str(Decimal(str(t)))} for s, n, t in rows}
    grand = sum((Decimal(v["total"]) for v in by_status.values()), Decimal("0"))
    return {"year": year, "month": month, "by_status": by_status, "total": str(grand)}
