from sqlalchemy.orm import Session
from models import AuditEvent


def record(db: Session, event_type: str, entity: str, entity_id, user_id: int | None = None, details: dict | None = None):
    """Registra uma linha na trilha de auditoria (o commit fica com quem chamou)."""
    db.add(AuditEvent(event_type=event_type, entity=entity, entity_id=str(entity_id),
                      user_id=user_id, details=details or {}))
