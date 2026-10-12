"""Acrescenta somente o feriado demonstrativo autorizado; nunca modifica schema."""
from datetime import date
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from backend import config
from backend.db.base import make_engine
from backend.db.models import Holiday, User
from backend.faturamento.service import record_audit

HOLIDAY_DATE = date(2026, 10, 12)
DESCRIPTION = 'Feriado de demonstração acadêmica'


def require_local_demo_database(url: str):
    target = make_url(url)
    if target.get_backend_name() != 'postgresql' or target.host not in ('127.0.0.1', 'localhost', '::1') or target.database != 'evchargeops':
        raise ValueError('Este script só pode executar no PostgreSQL local evchargeops de demonstração')


def register_demo_holiday(db: Session, actor_user_id: int):
    created = db.scalar(insert(Holiday).values(holiday_date=HOLIDAY_DATE, description=DESCRIPTION)
                        .on_conflict_do_nothing(index_elements=['holiday_date']).returning(Holiday.holiday_date))
    if created is not None:
        record_audit(db, entity_type='holiday', entity_id=HOLIDAY_DATE.isoformat(), action='demo_holiday_added',
                     actor_user_id=actor_user_id, after={'holiday_date': HOLIDAY_DATE.isoformat(), 'description': DESCRIPTION},
                     reason='Cenário acadêmico autorizado; calendário demonstrativo, não completo')
        db.flush()
    row = db.get(Holiday, HOLIDAY_DATE)
    return {'created': created is not None, 'holiday_date': row.holiday_date.isoformat(), 'description': row.description}


def main():
    require_local_demo_database(config.DATABASE_URL)
    engine = make_engine()
    try:
        with Session(engine) as db, db.begin():
            manager = db.scalar(select(User).where(User.email == 'sindico@demo.local', User.role == 'manager', User.active.is_(True)))
            if manager is None:
                raise ValueError('Conta demonstrativa do síndico não encontrada; nenhuma inclusão executada')
            result = register_demo_holiday(db, manager.id)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
