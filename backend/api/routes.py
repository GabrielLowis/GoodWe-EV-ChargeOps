from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session, selectinload
from backend.api.database import get_db
from backend.api.security import get_current_user, require_manager, create_token, hash_password, verify_password
from backend.api import schemas as s
from backend.db.models import (User, CondoUnit, Charger, Reservation, ChargingSession, Anomaly,
                              Tariff, TariffBand, TariffWindow, TaxRule, Invoice, AuditEvent)
from backend.faturamento import service as billing
from backend.faturamento.report import revenue_report
from backend.faturamento.mappers import tariff_to_spec
from backend.rateio.models import InvalidTariffError
from backend.api.pipeline import ingest
from backend.api.recommendation import recommend
from condocharge_ai.ml_model import carregar_modelo

router = APIRouter()


def commit(db):
    db.commit()


def visible(obj, user):
    if obj is None or (user.role != "manager" and obj.user_id != user.id):
        raise HTTPException(404, "Registro não encontrado")
    return obj


@router.get("/saude", response_model=s.HealthOut, tags=["infra"])
def health(db: Session = Depends(get_db)):
    try:
        version = db.scalar(text("SELECT version_num FROM alembic_version"))
        model = carregar_modelo()
    except Exception as exc:
        raise HTTPException(503, "Banco, migrations ou IA indisponíveis; consulte o log do backend") from exc
    return s.HealthOut(status="ok", database="ok", schema_version=version, ai_model=model["versao"])


@router.post("/login", response_model=s.TokenOut, tags=["auth"])
def login(body: s.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower(), User.active.is_(True)))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos")
    return s.TokenOut(access_token=create_token(user))


@router.get("/usuarios/eu", response_model=s.UserOut, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/usuarios", response_model=s.UserOut, status_code=201, tags=["auth"])
def register(body: s.UserCreate, db: Session = Depends(get_db)):
    if not db.get(CondoUnit, body.unit_id):
        raise HTTPException(422, "Unidade não encontrada")
    user = User(name=body.name, email=body.email.strip().lower(), unit_id=body.unit_id,
                role="resident", password_hash=hash_password(body.password))
    db.add(user)
    commit(db)
    return user


@router.get("/usuarios", response_model=list[s.UserOut], tags=["cadastros"])
def users(db: Session = Depends(get_db), _: User = Depends(require_manager)):
    return list(db.scalars(select(User).order_by(User.id)))


@router.get("/unidades", response_model=list[s.UnitOut], tags=["cadastros"])
def units(db: Session = Depends(get_db)):
    return list(db.scalars(select(CondoUnit).order_by(CondoUnit.id)))


@router.post("/unidades", response_model=s.UnitOut, status_code=201, tags=["cadastros"])
def create_unit(body: s.UnitCreate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    unit = CondoUnit(**body.model_dump())
    db.add(unit)
    commit(db)
    return unit


@router.get("/carregadores", response_model=list[s.ChargerOut], tags=["carregadores"])
def chargers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Charger).order_by(Charger.id)))


@router.post("/carregadores", response_model=s.ChargerOut, status_code=201, tags=["carregadores"])
def create_charger(body: s.ChargerCreate, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    charger = Charger(**body.model_dump())
    db.add(charger)
    commit(db)
    return charger


@router.get("/carregadores/{charger_id}/disponibilidade", response_model=s.AvailabilityOut, tags=["reservas"])
def availability(charger_id: int, start: s.AwareDatetime, end: s.AwareDatetime,
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    charger = db.get(Charger, charger_id)
    if not charger or not charger.active:
        raise HTTPException(404, "Carregador indisponível")
    if not start < end <= start + timedelta(days=7):
        raise HTTPException(422, "Consultar intervalo positivo de até sete dias")
    busy = db.scalars(select(Reservation).where(Reservation.charger_id == charger_id,
                                               Reservation.status.in_(["active", "in_use"]),
                                               Reservation.starts_at < end, Reservation.ends_at > start)
                      .order_by(Reservation.starts_at))
    # Não expõe nomes nem ids de outros moradores para consultar a agenda.
    return s.AvailabilityOut(charger_id=charger_id, connectors=charger.connectors,
                             busy=[s.BusyWindow.model_validate(r) for r in busy])


@router.get("/reservas", response_model=list[s.ReservationOut], tags=["reservas"])
def reservations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Reservation).order_by(Reservation.starts_at.desc())
    if user.role != "manager":
        stmt = stmt.where(Reservation.user_id == user.id)
    return list(db.scalars(stmt))


@router.post("/reservas", response_model=s.ReservationOut, status_code=201, tags=["reservas"])
def create_reservation(body: s.ReservationCreate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    # Mesmo lock usado no ingresso da sessão. EXCLUDE no Postgres é a última defesa contra corrida.
    charger = db.scalar(select(Charger).where(Charger.id == body.charger_id).with_for_update())
    now = datetime.now(UTC)
    if not charger or not charger.active or body.connector > charger.connectors:
        raise HTTPException(422, "Carregador/conector indisponível")
    if body.starts_at <= now:
        raise HTTPException(422, "Reserva precisa começar no futuro")
    if user.reservation_blocked_until and user.reservation_blocked_until > now:
        raise HTTPException(403, "Reservas temporariamente bloqueadas por faltas")
    conflict = db.scalar(select(Reservation.id).where(
        Reservation.charger_id == body.charger_id, Reservation.connector == body.connector,
        Reservation.status.in_(["active", "in_use"]),
        Reservation.starts_at < body.ends_at, Reservation.ends_at > body.starts_at))
    if conflict:
        raise HTTPException(409, "Janela já reservada")
    row = Reservation(**body.model_dump(), user_id=user.id, status="active")
    db.add(row)
    db.flush()
    billing.record_audit(db, entity_type="reservation", entity_id=row.id, action="reservation_created",
                         actor_user_id=user.id)
    commit(db)
    return row


@router.post("/reservas/{reservation_id}/cancelar", response_model=s.ReservationOut, tags=["reservas"])
def cancel(reservation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = visible(db.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update()), user)
    if row.status != "active":
        raise HTTPException(409, "Só é possível cancelar uma reserva ativa")
    if row.starts_at <= datetime.now(UTC):
        raise HTTPException(409, "Só é possível cancelar antes do início da reserva")
    row.status, row.cancelled_at = "cancelled", datetime.now(UTC)
    billing.record_audit(db, entity_type="reservation", entity_id=row.id, action="reservation_cancelled",
                         actor_user_id=user.id)
    commit(db)
    return row


@router.post("/reservas/no-show/processar", response_model=list[s.ReservationOut], tags=["reservas"])
def no_show(db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    now = datetime.now(UTC)
    rows = list(db.scalars(select(Reservation).where(Reservation.status == "active",
                                                   Reservation.starts_at < now-timedelta(minutes=20))
                           .with_for_update()))
    for row in rows:
        row.status = "no_show"
        billing.record_audit(db, entity_type="reservation", entity_id=row.id, action="no_show",
                             actor_user_id=manager.id)
        db.flush()
        count = db.scalar(select(func.count()).select_from(Reservation).where(
            Reservation.user_id == row.user_id, Reservation.status == "no_show",
            Reservation.starts_at >= now-timedelta(days=30)))
        if count >= 3:
            owner = db.get(User, row.user_id)
            owner.reservation_blocked_until = now + timedelta(days=7)
    commit(db)
    return rows


@router.post("/sessoes", response_model=s.IngestOut, status_code=201, tags=["sessoes"])
def ingest_session(body: s.SessionIn, db: Session = Depends(get_db), _: User = Depends(require_manager)):
    result = ingest(db, body)
    commit(db)
    return result


@router.get("/sessoes", response_model=list[s.SessionOut], tags=["sessoes"])
def sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ChargingSession).order_by(ChargingSession.started_at.desc())
    if user.role != "manager":
        stmt = stmt.where(ChargingSession.user_id == user.id)
    return list(db.scalars(stmt))


@router.get("/sessoes/{session_id}", response_model=s.SessionOut, tags=["sessoes"])
def session_detail(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return visible(db.get(ChargingSession, session_id), user)


@router.get("/anomalias", response_model=list[s.AnomalyOut], tags=["anomalias"])
def anomalies(status: str = "pending_review", db: Session = Depends(get_db),
              _: User = Depends(require_manager)):
    if status not in ("pending_review", "approved", "rejected"):
        raise HTTPException(422, "Status inválido")
    return list(db.scalars(select(Anomaly).where(Anomaly.status == status).order_by(Anomaly.detected_at.desc())))


@router.post("/anomalias/{anomaly_id}/revisao", response_model=s.AnomalyOut, tags=["anomalias"])
def review(anomaly_id: int, body: s.ReviewIn, db: Session = Depends(get_db),
           manager: User = Depends(require_manager)):
    anomaly = db.scalar(select(Anomaly).where(Anomaly.id == anomaly_id).with_for_update())
    if anomaly is None:
        raise HTTPException(404, "Anomalia não encontrada")
    if anomaly.status != "pending_review":
        raise HTTPException(409, "Anomalia já revisada")
    session = db.get(ChargingSession, anomaly.session_id)
    if body.user_id is not None:
        if session.reservation_id is not None:
            raise HTTPException(422, "Sessão com reserva mantém o morador da reserva")
        target = db.get(User, body.user_id)
        if not target or target.role != "resident" or not target.active:
            raise HTTPException(422, "Morador indisponível")
        session.user_id, session.attribution_method = target.id, "manual"
        db.flush()
    if body.decision == "approve" and session.user_id is None:
        raise HTTPException(422, "Informe o morador antes de aprovar a sessão órfã")
    billing.review_anomaly(db, anomaly_id, "approved" if body.decision == "approve" else "rejected",
                           manager.id, body.note)
    commit(db)
    return anomaly


@router.get("/tarifas", response_model=list[s.TariffOut], tags=["configuracao"])
def tariffs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Tariff).options(selectinload(Tariff.bands), selectinload(Tariff.windows))
                           .order_by(Tariff.valid_from.desc())))


@router.post("/tarifas", response_model=s.TariffOut, status_code=201, tags=["configuracao"])
def tariff_create(body: s.TariffCreate, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    if len({b.band for b in body.bands}) != len(body.bands):
        raise HTTPException(422, "Faixas duplicadas")
    row = Tariff(**body.model_dump(exclude={"bands", "windows"}))
    row.bands = [TariffBand(**b.model_dump()) for b in body.bands]
    row.windows = [TariffWindow(**w.model_dump()) for w in body.windows]
    try:
        tariff_to_spec(row).validate()
    except InvalidTariffError as exc:
        raise HTTPException(422, str(exc)) from exc
    # Vigências [início, fim). Fechar só a versão aberta antes de inserir a nova.
    previous = db.scalar(select(Tariff).where(Tariff.valid_to.is_(None)).with_for_update())
    if previous:
        if body.valid_from <= previous.valid_from:
            raise HTTPException(409, "Nova versão deve começar após a versão aberta")
        previous.valid_to = body.valid_from
        db.flush()
    db.add(row)
    db.flush()
    billing.record_audit(db, entity_type="tariff", entity_id=row.id, action="tariff_version_created",
                         actor_user_id=manager.id)
    commit(db)
    return row


@router.get("/impostos", response_model=list[s.TaxOut], tags=["configuracao"])
def taxes(db: Session = Depends(get_db), _: User = Depends(require_manager)):
    return list(db.scalars(select(TaxRule).order_by(TaxRule.valid_from.desc())))


@router.post("/impostos", response_model=s.TaxOut, status_code=201, tags=["configuracao"])
def tax_create(body: s.TaxCreate, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    previous = db.scalar(select(TaxRule).where(TaxRule.tax_type == body.tax_type,
                                              TaxRule.jurisdiction == body.jurisdiction,
                                              TaxRule.valid_to.is_(None)).with_for_update())
    if previous:
        if body.valid_from <= previous.valid_from:
            raise HTTPException(409, "Nova versão deve começar após a versão aberta")
        previous.valid_to = body.valid_from
        db.flush()
    row = TaxRule(**body.model_dump())
    db.add(row)
    db.flush()
    billing.record_audit(db, entity_type="tax_rule", entity_id=row.id, action="tax_version_created",
                         actor_user_id=manager.id)
    commit(db)
    return row


@router.post("/faturas/gerar", response_model=list[s.InvoiceOut], tags=["faturas"])
def generate(body: s.InvoiceGenerate, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    # Evita corrida ao gerar a primeira fatura, quando ainda não há linha para FOR UPDATE.
    db.execute(text("SELECT pg_advisory_xact_lock(902105)"))
    period = date(body.year, body.month, 1)
    if body.user_id:
        target = db.get(User, body.user_id)
        if not target or target.role != "resident":
            raise HTTPException(404, "Morador não encontrado")
        rows = [billing.generate_invoice(db, body.user_id, period, actor_user_id=manager.id)]
    else:
        rows = billing.generate_invoices_for_period(db, period, actor_user_id=manager.id)
    commit(db)
    return rows


@router.get("/faturas", response_model=list[s.InvoiceOut], tags=["faturas"])
def invoices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Invoice).options(selectinload(Invoice.items)).order_by(Invoice.period.desc())
    if user.role != "manager":
        stmt = stmt.where(Invoice.user_id == user.id)
    return list(db.scalars(stmt))


@router.get("/faturas/{invoice_id}", response_model=s.InvoiceOut, tags=["faturas"])
def invoice_detail(invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return visible(db.get(Invoice, invoice_id), user)


@router.post("/faturas/{invoice_id}/fechar", response_model=s.InvoiceOut, tags=["faturas"])
def close(invoice_id: int, db: Session = Depends(get_db), manager: User = Depends(require_manager)):
    if not db.get(Invoice, invoice_id):
        raise HTTPException(404, "Fatura não encontrada")
    row = billing.close_invoice(db, invoice_id, manager.id)
    commit(db)
    return row


@router.get("/relatorios/arrecadacao", response_model=dict, tags=["financeiro"])
def report(year: int = Query(ge=2000, le=2100), month: int = Query(ge=1, le=12),
           db: Session = Depends(get_db), _: User = Depends(require_manager)):
    result = revenue_report(db, date(year, month, 1))
    result["scope"] = "Valores faturados; pagamentos e recebimentos não são registrados neste MVP."
    return result


@router.get("/recomendacao-janela", response_model=s.RecommendationOut, tags=["recomendacao"])
def recommendation(charger_id: int, kwh: Decimal = Query(gt=0, le=200, decimal_places=3),
                   power_kw: Decimal = Query(default=Decimal("3.3"), gt=0, le=22, decimal_places=2),
                   db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    charger = db.get(Charger, charger_id)
    if not charger or not charger.active:
        raise HTTPException(404, "Carregador indisponível")
    return recommend(db, charger, kwh, power_kw)
