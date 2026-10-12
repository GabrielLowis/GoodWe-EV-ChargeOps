from datetime import UTC, datetime, time
from decimal import Decimal
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.tests.conftest import db_engine, db  # noqa: F401
from backend.api.database import get_db
from backend.api.security import hash_password
from backend.db.models import User, CondoUnit, Charger, Tariff, TariffBand, TaxRule
from backend.main import app


@pytest.fixture
def api(db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "integration-tests-only-0123456789abcdef0123456789")
    unit = CondoUnit(number="101", block="T")
    db.add(unit)
    db.flush()
    manager = User(name="Síndico", email="manager@test.local", role="manager", password_hash=hash_password("TestPass123!"))
    resident = User(name="Morador", email="resident@test.local", role="resident", unit_id=unit.id,
                    password_hash=hash_password("TestPass123!"))
    other = User(name="Outro", email="other@test.local", role="resident", unit_id=unit.id,
                 password_hash=hash_password("TestPass123!"))
    charger = Charger(code="HCA01", serial_number="INTEGRATION", model="HCA", rated_power_kw=Decimal("7"), connectors=1)
    tariff = Tariff(name="Teste", valid_from=datetime(2026, 1, 1, tzinfo=UTC), idle_fee_per_minute=Decimal("0.25"),
                    overhead_percent=Decimal("5"))
    tariff.bands = [TariffBand(band="off_peak", green_price_per_kwh=Decimal("0.30"), grid_price_per_kwh=Decimal("0.65"))]
    tax = TaxRule(tax_type="iss", jurisdiction="BR-SP-SAO_PAULO", rate_percent=Decimal("5"),
                  valid_from=datetime(2026, 1, 1, tzinfo=UTC))
    db.add_all([manager, resident, other, charger, tariff, tax])
    db.flush()

    def override():
        try:
            yield db
        except Exception:
            db.rollback()
            raise
    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        headers = {}
        for label, user in [("manager", manager), ("resident", resident), ("other", other)]:
            response = client.post("/api/login", json={"email": user.email, "password": "TestPass123!"})
            assert response.status_code == 200, response.text
            headers[label] = {"Authorization": "Bearer " + response.json()["access_token"]}
        yield SimpleNamespace(client=client, db=db, manager=manager, resident=resident, other=other,
                              charger=charger, tariff=tariff, headers=headers)
    app.dependency_overrides.clear()
