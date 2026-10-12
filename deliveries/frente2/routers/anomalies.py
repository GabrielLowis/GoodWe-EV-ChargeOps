from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Anomaly, AnomalyStatus, User
from schemas import AnomalyOut, ReviewIn
from security import require_manager
from services.pipeline import review_anomaly, ReviewError

router = APIRouter(tags=["Anomalias (fila do sindico)"])


@router.get("/anomalias", response_model=list[AnomalyOut])
def list_anomalies(status: str = "Pending", db: Session = Depends(get_db), _: User = Depends(require_manager)):
    try:
        wanted = AnomalyStatus(status)
    except ValueError:
        raise HTTPException(422, "status deve ser Pending, Approved ou Rejected")
    rows = db.scalars(select(Anomaly).where(Anomaly.status == wanted).order_by(Anomaly.created_at)).all()
    return [AnomalyOut.from_anomaly(a) for a in rows]


@router.post("/anomalias/{anomaly_id}/revisao", response_model=AnomalyOut)
def review(anomaly_id: int, body: ReviewIn, db: Session = Depends(get_db),
           manager: User = Depends(require_manager)):
    anomaly = db.get(Anomaly, anomaly_id)
    if anomaly is None:
        raise HTTPException(404, "Anomalia nao encontrada")
    try:
        review_anomaly(db, anomaly, manager, body.decision, body.user_id)
    except ReviewError as e:
        raise HTTPException(e.status_code, e.detail)
    return AnomalyOut.from_anomaly(anomaly)
