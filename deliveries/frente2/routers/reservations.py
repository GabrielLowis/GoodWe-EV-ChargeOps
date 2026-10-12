import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Reservation, ReservationStatus, Charger, User, ProfileUser
from schemas import ReservationCreate, ReservationOut
from security import get_current_user, require_manager
from services import audit
from services.reservations import (count_overlaps, max_concurrent, process_no_shows,
                                   MAX_RESERVATION_HOURS)

router = APIRouter(tags=["Reservas"])


@router.post("/reservas", response_model=ReservationOut, status_code=201)
def create_reservation(body: ReservationCreate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    if db.get(Charger, body.charger_id) is None:
        raise HTTPException(404, "Carregador nao encontrado")
    if body.ended_at <= body.started_at:
        raise HTTPException(422, "O fim da reserva deve ser depois do inicio")
    if (body.ended_at - body.started_at) > datetime.timedelta(hours=MAX_RESERVATION_HOURS):
        raise HTTPException(422, f"Reserva maxima de {MAX_RESERVATION_HOURS} horas")
    if count_overlaps(db, body.charger_id, body.started_at, body.ended_at) >= max_concurrent():
        raise HTTPException(409, "Janela indisponivel: capacidade do carregador atingida")

    reservation = Reservation(user_id=user.id, charger_id=body.charger_id, started_at=body.started_at,
                              ended_at=body.ended_at, status=ReservationStatus.Await)
    db.add(reservation)
    db.flush()
    audit.record(db, "RESERVATION_CREATED", "reservation", reservation.id, user.id)
    db.commit()
    return ReservationOut.from_res(reservation)


@router.get("/reservas", response_model=list[ReservationOut])
def list_reservations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Reservation).order_by(Reservation.started_at)
    if user.profile != ProfileUser.Gestor:
        stmt = stmt.where(Reservation.user_id == user.id)
    return [ReservationOut.from_res(r) for r in db.scalars(stmt).all()]


@router.post("/reservas/no-show/processar")
def run_no_show(db: Session = Depends(get_db), _: User = Depends(require_manager)):
    """Cancela reservas sem sessao apos 20 min do inicio e registra reincidencia."""
    return {"processed": process_no_shows(db, datetime.datetime.now())}


@router.post("/reservas/{reservation_id}/cancelar", response_model=ReservationOut)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(404, "Reserva nao encontrada")
    if reservation.user_id != user.id and user.profile != ProfileUser.Gestor:
        raise HTTPException(403, "Voce so pode cancelar suas proprias reservas")
    if reservation.status != ReservationStatus.Await:
        raise HTTPException(409, "Apenas reservas ativas podem ser canceladas")
    reservation.status = ReservationStatus.Cancelled
    audit.record(db, "RESERVATION_CANCELLED", "reservation", reservation.id, user.id)
    db.commit()
    return ReservationOut.from_res(reservation)
