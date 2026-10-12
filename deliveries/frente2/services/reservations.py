import datetime
import os
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models import Reservation, ReservationStatus, AuditEvent
from services import audit

NO_SHOW_MINUTES = int(os.getenv("NO_SHOW_MINUTES", "20"))
MAX_RESERVATION_HOURS = 12


def max_concurrent() -> int:
    """Capacidade simultanea do carregador (parametrizavel por variavel de ambiente)."""
    return int(os.getenv("MAX_CONCURRENT_RESERVATIONS", "1"))


def count_overlaps(db: Session, charger_id: str, start: datetime.datetime, end: datetime.datetime) -> int:
    """Quantas reservas ativas se sobrepoem a janela [start, end)."""
    stmt = select(func.count()).select_from(Reservation).where(
        Reservation.charger_id == charger_id,
        Reservation.status == ReservationStatus.Await,
        Reservation.started_at < end,
        Reservation.ended_at > start,
    )
    return db.scalar(stmt)


def find_active_reservation(db: Session, charger_id: str, moment: datetime.datetime) -> Reservation | None:
    """Reserva ativa do carregador cuja janela contem o instante em que a sessao comecou."""
    stmt = select(Reservation).where(
        Reservation.charger_id == charger_id,
        Reservation.status == ReservationStatus.Await,
        Reservation.started_at <= moment,
        Reservation.ended_at >= moment,
    ).order_by(Reservation.started_at)
    return db.scalars(stmt).first()


def process_no_shows(db: Session, now: datetime.datetime) -> list[dict]:
    """Cancela reservas sem sessao apos NO_SHOW_MINUTES do inicio e registra a reincidencia."""
    limit = now - datetime.timedelta(minutes=NO_SHOW_MINUTES)
    stmt = select(Reservation).where(Reservation.status == ReservationStatus.Await,
                                     Reservation.started_at < limit)
    result = []
    for r in db.scalars(stmt).all():
        r.status = ReservationStatus.No_show
        previous = db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.event_type == "NO_SHOW", AuditEvent.user_id == r.user_id))
        reincidence = previous + 1
        audit.record(db, "NO_SHOW", "reservation", r.id, r.user_id,
                     {"charger_id": r.charger_id, "reincidence": reincidence})
        result.append({"reservation_id": r.id, "user_id": r.user_id, "no_shows_total": reincidence})
    db.commit()
    return result
