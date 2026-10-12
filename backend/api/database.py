from sqlalchemy.orm import Session
from backend.db.base import make_engine, make_session_factory

engine = make_engine(pool_pre_ping=True)
SessionLocal = make_session_factory(engine)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
