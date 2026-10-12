import os

# Variaveis falsas: o engine do PostgreSQL e criado ao importar, mas os testes usam SQLite em memoria.
os.environ.update(DB_USER="t", DB_PASSWORD="t", DB_HOST="localhost", DB_PORT="5432", DB_NAME="t",
                  JWT_SECRET="segredo-de-teste-com-mais-de-32-caracteres-ok")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base
from seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        seed(session)
        yield session
    engine.dispose()


@pytest.fixture()
def client(db):
    def override():
        yield db
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(client, email, password):
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def manager(client):
    return _login(client, "sindico@demo.com", "gestor-demo-123")


@pytest.fixture()
def resident(client):
    return _login(client, "morador@demo.com", "morador-demo-123")


def make_session(**over):
    """Sessao valida do PDF; cada teste altera so o que precisa."""
    base = {
        "session_id": "abc123", "charger_id": "HCA01", "card_id": "RFID-05",
        "started_at": "2026-09-22T19:00:00", "ended_at": "2026-09-22T21:10:00",
        "total_kwh": 14.8, "green_kwh": 4.2, "grid_kwh": 10.6,
        "average_power_kw": 6.8, "max_power_kw": 7.1, "status": "completed",
    }
    base.update(over)
    return base


def reserve(client, headers, start="2026-09-22T18:50:00", end="2026-09-22T21:30:00", charger="HCA01"):
    return client.post("/reservas", headers=headers,
                       json={"charger_id": charger, "started_at": start, "ended_at": end})
