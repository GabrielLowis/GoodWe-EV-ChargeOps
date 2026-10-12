"""Pipeline de ingestao: sessao -> atribuicao -> validacao/IA -> aprovada ou fila do sindico."""
import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.anomaly import check_session
from models import (ChargingSession, ChargingStatus, ProcessingStatus, ReservationStatus,
                    Anomaly, AnomalyStatus, User)
from schemas import SessionDTO
from services import audit
from services.reservations import find_active_reservation

ORPHAN_REASON = {
    "code": "ORPHAN_SESSION",
    "message": "Sessao sem reserva correspondente: o sindico precisa indicar o morador.",
}


def ingest_session(db: Session, dto: SessionDTO) -> tuple[ChargingSession, Anomaly | None, list[dict]]:
    session = ChargingSession(
        session_id=dto.session_id, charger_id=dto.charger_id, card_id=dto.card_id,
        started_at=dto.started_at, ended_at=dto.ended_at,
        total_kwh=dto.total_kwh, green_kwh=dto.green_kwh, grid_kwh=dto.grid_kwh,
        average_power_kw=dto.average_power_kw, max_power_kw=dto.max_power_kw,
        status=ChargingStatus[dto.status], processing_status=ProcessingStatus.Received,
    )
    db.add(session)

    # 1) Atribuicao: a reserva ativa na janela de tempo define o morador.
    reservation = find_active_reservation(db, dto.charger_id, dto.started_at)
    if reservation:
        session.reservation_id = reservation.id
        session.user_id = reservation.user_id
        reservation.status = ReservationStatus.Completed
    db.flush()

    # 2) Validacao estrutural, fisica e ML.
    result = check_session(dto)
    reasons = list(result.reasons)
    if session.user_id is None:
        reasons.append(ORPHAN_REASON)

    anomaly = None
    if reasons:
        session.processing_status = (ProcessingStatus.Suspended if result.status == "suspended"
                                     else ProcessingStatus.Orphan)
        anomaly = Anomaly(session_id=session.session_id, layer_failed=result.layer_failed,
                          score=result.score, reasons=reasons, status=AnomalyStatus.Pending)
        db.add(anomaly)
        db.flush()
        audit.record(db, "SESSION_SENT_TO_REVIEW", "session", session.session_id,
                     details={"anomaly_id": anomaly.id, "layer_failed": result.layer_failed,
                              "codes": [r["code"] for r in reasons]})
    else:
        session.processing_status = ProcessingStatus.Approved

    audit.record(db, "SESSION_INGESTED", "session", session.session_id,
                 session.user_id, {"processing_status": session.processing_status.value})
    db.commit()
    return session, anomaly, reasons


class ReviewError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def review_anomaly(db: Session, anomaly: Anomaly, reviewer: User, decision: str, user_id: int | None):
    if anomaly.status != AnomalyStatus.Pending:
        raise ReviewError(409, "Anomalia ja revisada")
    session = db.get(ChargingSession, anomaly.session_id)

    if decision == "approve":
        if user_id is not None:
            if db.get(User, user_id) is None:
                raise ReviewError(404, "Morador informado nao existe")
            session.user_id = user_id
        if session.user_id is None:
            raise ReviewError(422, "Sessao sem morador: informe user_id para aprovar")
        session.processing_status = ProcessingStatus.Approved
        anomaly.status = AnomalyStatus.Approved
    else:
        session.processing_status = ProcessingStatus.Rejected
        anomaly.status = AnomalyStatus.Rejected

    anomaly.reviewed_by = reviewer.id
    anomaly.reviewed_at = datetime.datetime.now()
    audit.record(db, "ANOMALY_REVIEWED", "anomaly", anomaly.id, reviewer.id,
                 {"decision": decision, "session_id": session.session_id, "assigned_user_id": session.user_id})
    db.commit()
    return anomaly
