from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.api.detection import detect
from backend.api.schemas import SessionIn, IngestOut, SessionOut, DetectionOut
from backend.db.models import Charger, ChargingSession, Reservation, SessionPowerSample, Anomaly, AuditEvent
from backend.faturamento.service import record_audit


def ingest(db: Session, dto: SessionIn) -> IngestOut:
    # Serializa eventos/reservas deste equipamento e elimina a corrida de INSERT/idempotência.
    charger = db.scalar(select(Charger).where(Charger.code == dto.charger_id).with_for_update())
    if not charger or not charger.active:
        raise HTTPException(422, "Carregador indisponível")
    if dto.connector > charger.connectors:
        raise HTTPException(422, "Conector inexistente")
    existing = db.scalar(select(ChargingSession).where(ChargingSession.source == dto.source,
                                                     ChargingSession.external_id == dto.session_id))
    payload = dto.model_dump(mode="json")
    if existing:
        event = db.scalar(select(AuditEvent).where(AuditEvent.entity_type == "charging_session",
                                                  AuditEvent.entity_id == str(existing.id),
                                                  AuditEvent.action == "session_ingested"))
        if not event or event.after_data["payload"] != payload:
            raise HTTPException(409, "Identificador já recebido com dados diferentes; requer reconciliação")
        anomaly = db.scalar(select(Anomaly).where(Anomaly.session_id == existing.id))
        return IngestOut(session=SessionOut.model_validate(existing), anomaly_id=anomaly.id if anomaly else None,
                         duplicate=True, detection=DetectionOut.model_validate(event.after_data["detection"]))

    # Uma fonte secundária não pode atribuir/faturar novamente a mesma recarga física.
    overlap = db.scalar(select(ChargingSession.id).where(
        ChargingSession.charger_id == charger.id, ChargingSession.connector == dto.connector,
        ChargingSession.started_at < dto.ended_at, ChargingSession.ended_at > dto.started_at))
    if overlap:
        raise HTTPException(409, "Sessão física sobreposta: conferir as fontes antes de importar")
    reservation = db.scalar(select(Reservation).where(
        Reservation.charger_id == charger.id, Reservation.connector == dto.connector,
        Reservation.status.in_(["active", "in_use"]),
        Reservation.starts_at <= dto.started_at, Reservation.ends_at > dto.started_at).with_for_update())
    detection = detect(dto, charger)
    if reservation is None:
        detection.is_anomaly = True
        detection.reasons.append("ORPHAN_SESSION")
        detection.reasons_human.append("Sem reserva correspondente; síndico deve atribuir o morador.")
        if detection.layer == "passed":
            detection.layer = "attribution"
    session = ChargingSession(source=dto.source, external_id=dto.session_id, charger_id=charger.id,
                              connector=dto.connector, card_id=dto.card_id, started_at=dto.started_at,
                              energy_ended_at=dto.energy_ended_at, ended_at=dto.ended_at,
                              total_kwh=dto.total_kwh, green_kwh=dto.green_kwh, grid_kwh=dto.grid_kwh,
                              average_power_kw=dto.average_power_kw, max_power_kw=dto.max_power_kw,
                              end_status="completed" if dto.status == "abnormal_disconnection" else dto.status,
                              failure_code=dto.failure_code,
                              validation_status="suspended" if detection.is_anomaly else "approved",
                              user_id=reservation.user_id if reservation else None,
                              reservation_id=reservation.id if reservation else None,
                              attribution_method="reservation" if reservation else "unattributed")
    session.samples = [SessionPowerSample(**s.model_dump()) for s in dto.power_samples]
    if reservation:
        reservation.status = "completed"
    db.add(session)
    db.flush()
    anomaly = None
    if detection.is_anomaly:
        anomaly = Anomaly(session_id=session.id, detector=detection.layer,
                          score=Decimal(str(detection.score)) if detection.score is not None else None,
                          reasons=[{"code": c, "message": m, "model_version": detection.model_version}
                                   for c, m in zip(detection.reasons, detection.reasons_human)],
                          status="pending_review")
        db.add(anomaly)
        db.flush()
    record_audit(db, entity_type="charging_session", entity_id=session.id, action="session_ingested",
                 after={"payload": payload, "detection": detection.model_dump(mode="json")})
    db.flush()
    return IngestOut(session=SessionOut.model_validate(session), anomaly_id=anomaly.id if anomaly else None,
                     duplicate=False, detection=detection)
