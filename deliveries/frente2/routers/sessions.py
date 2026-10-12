from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import ChargingSession, Charger, User, ProfileUser
from schemas import SessionDTO, SessionOut, IngestResult
from security import get_current_user
from services.pipeline import ingest_session

router = APIRouter(tags=["Sessoes"])


@router.post("/sessoes", response_model=IngestResult, status_code=201)
def create_session(dto: SessionDTO, db: Session = Depends(get_db)):
    """Recebe uma sessao (SessionDTO), atribui ao morador, valida e decide o destino.

    Endpoint de ingestao (gateway/cliente SEMS). Nesta versao e aberto; ver README (limitacoes).
    """
    if db.get(Charger, dto.charger_id) is None:
        raise HTTPException(422, f"Carregador {dto.charger_id} nao cadastrado")
    if db.get(ChargingSession, dto.session_id) is not None:
        raise HTTPException(409, "Sessao ja cadastrada")
    session, anomaly, reasons = ingest_session(db, dto)
    return IngestResult(session_id=session.session_id, processing_status=session.processing_status.value,
                        reservation_id=session.reservation_id, user_id=session.user_id,
                        anomaly_id=anomaly.id if anomaly else None, reasons=reasons)


@router.get("/sessoes", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ChargingSession).order_by(ChargingSession.started_at.desc())
    if user.profile != ProfileUser.Gestor:
        stmt = stmt.where(ChargingSession.user_id == user.id)
    return [SessionOut.from_session(s) for s in db.scalars(stmt).all()]


@router.get("/sessoes/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(ChargingSession, session_id)
    if s is None or (user.profile != ProfileUser.Gestor and s.user_id != user.id):
        raise HTTPException(404, "Sessao nao encontrada")
    return SessionOut.from_session(s)
