from datetime import datetime, UTC, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select, func
from backend.db.models import AuditEvent, Reservation, InvoiceItem, ChargingSession
from backend.api.schemas import SessionIn

pytestmark = pytest.mark.db


def reserve(api, hours=3):
    start = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
    end = start + timedelta(hours=hours)
    response = api.client.post("/api/reservas", headers=api.headers["resident"], json={
        "charger_id": api.charger.id, "starts_at": start.isoformat(), "ends_at": end.isoformat()})
    assert response.status_code == 201, response.text
    return start, end, response.json()


def payload(start, end, **extra):
    return {"source": "simulator", "session_id": "test-session", "charger_id": "HCA01", "card_id": "SHARED",
            "started_at": start.isoformat(), "ended_at": end.isoformat(), "energy_ended_at": end.isoformat(),
            "total_kwh": "6.200", "green_kwh": "1.000", "grid_kwh": "5.200",
            "average_power_kw": "2.30", "max_power_kw": "3.30", "status": "completed", **extra}


def ingest(api, body):
    response = api.client.post("/api/sessoes", headers=api.headers["manager"], json=body)
    assert response.status_code == 201, response.text
    return response.json()


def approve(api, result, **extra):
    if result["anomaly_id"]:
        response = api.client.post(f"/api/anomalias/{result['anomaly_id']}/revisao",
                                   headers=api.headers["manager"], json={"decision": "approve", **extra})
        assert response.status_code == 200, response.text


def invoice(api, start):
    response = api.client.post("/api/faturas/gerar", headers=api.headers["manager"],
                               json={"user_id": api.resident.id, "year": start.year, "month": start.month})
    assert response.status_code == 200, response.text
    return response.json()[0]


def test_http_reservation_ai_rateio_invoice_and_permissions(api, monkeypatch):
    start, end, reservation = reserve(api)
    result = ingest(api, payload(start, end))
    assert result["session"]["user_id"] == api.resident.id
    assert result["session"]["reservation_id"] == reservation["id"]
    assert result["detection"]["model_version"] == "v1.0.0"
    approve(api, result)
    inv = invoice(api, start)
    assert len(inv["items"]) == 1
    assert inv["items"][0]["session_id"] == result["session"]["id"]
    assert Decimal(inv["total"]) == Decimal("4.04")  # subtotal 3.68 + imposto .18 + overhead .18
    assert inv["items"][0]["calculation"]["tariff"]["name"] == "Teste"
    assert api.client.get(f"/api/faturas/{inv['id']}", headers=api.headers["other"]).status_code == 404
    assert api.client.get("/api/anomalias", headers=api.headers["resident"]).status_code == 403
    assert api.client.post("/api/faturas/gerar", headers=api.headers["resident"], json={
        "year": start.year, "month": start.month}).status_code == 403
    again = invoice(api, start)
    assert len(again["items"]) == 1 and again["total"] == inv["total"]
    assert api.db.scalar(select(func.count()).select_from(InvoiceItem)) == 1
    from backend import config
    from backend.faturamento import service as billing
    from backend.faturamento.periods import month_bounds

    assert api.client.post(f"/api/faturas/{inv['id']}/fechar", headers=api.headers["manager"]).status_code == 409
    period_end = month_bounds(datetime.fromisoformat(inv['period']).date(), config.CONDO_TIMEZONE)[1]

    class ClosingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return period_end

    monkeypatch.setattr(billing, 'datetime', ClosingClock)
    closed = api.client.post(f"/api/faturas/{inv['id']}/fechar", headers=api.headers["manager"])
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
    assert api.client.post("/api/faturas/gerar", headers=api.headers["manager"], json={
        "year": start.year, "month": start.month, "user_id": api.resident.id}).status_code == 409


def test_idempotent_ingestion_and_conflicting_duplicate(api):
    start, end, _ = reserve(api)
    body = payload(start, end)
    first = ingest(api, body)
    second = ingest(api, body)
    assert second["duplicate"] and first["session"]["id"] == second["session"]["id"]
    response = api.client.post("/api/sessoes", headers=api.headers["manager"], json={**body, "card_id": "DIFFERENT"})
    assert response.status_code == 409
    assert api.db.scalar(select(func.count()).select_from(ChargingSession)) == 1
    assert api.client.post("/api/sessoes", headers=api.headers["resident"], json=body).status_code == 403
    assert api.client.post("/api/sessoes", json=body).status_code == 401


def test_agenda_conflict_and_privacy(api):
    start, end, _ = reserve(api)
    body = {"charger_id": api.charger.id, "starts_at": start.isoformat(), "ends_at": end.isoformat()}
    assert api.client.post("/api/reservas", headers=api.headers["other"], json=body).status_code == 409
    busy = api.client.get(f"/api/carregadores/{api.charger.id}/disponibilidade", headers=api.headers["other"],
                          params={"start": start.isoformat(), "end": end.isoformat()}).json()["busy"]
    assert len(busy) == 1 and set(busy[0]) == {"connector", "starts_at", "ends_at"}
    assert api.client.get("/api/reservas", headers=api.headers["other"]).json() == []


def test_orphan_assignment_review_and_audit(api):
    start = datetime.now(UTC) + timedelta(days=1)
    result = ingest(api, payload(start, start + timedelta(hours=3)))
    assert "ORPHAN_SESSION" in result["detection"]["reasons"]
    assert result["session"]["user_id"] is None
    assert api.client.post(f"/api/anomalias/{result['anomaly_id']}/revisao", headers=api.headers["manager"],
                           json={"decision": "approve"}).status_code == 422
    approve(api, result, user_id=api.resident.id)
    inv = invoice(api, start)
    assert len(inv["items"]) == 1
    assert api.db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "anomaly_review")) == 1


def test_system_failure_has_zero_charge(api):
    start, end, _ = reserve(api)
    result = ingest(api, payload(start, end, status="system_failure", failure_code="DEMO-FAILURE"))
    approve(api, result)
    inv = invoice(api, start)
    assert inv["total"] == "0.00"
    assert inv["items"][0]["charge_rule"] == "system_failure_no_charge"


def test_no_energy_end_evidence_does_not_invent_idle(api):
    start, end, _ = reserve(api)
    result = ingest(api, payload(start, end, energy_ended_at=None))
    approve(api, result)
    inv = invoice(api, start)
    assert inv["idle_minutes"] == 0
    assert inv["idle_amount"] == "0.00"


def test_physical_anomaly_is_suspended_and_not_billed(api):
    start, end, _ = reserve(api)
    result = ingest(api, payload(start, end, max_power_kw="15.00"))
    assert result["session"]["validation_status"] == "suspended"
    assert "POWER_EXCEEDS_NOMINAL" in result["detection"]["reasons"]
    inv = invoice(api, start)
    assert inv["total"] == "0.00" and inv["sessions_count"] == 0
    assert inv["calculation"]["notes"]


def test_naive_datetime_and_invalid_status_rejected(api):
    start, end, _ = reserve(api)
    body = payload(start, end)
    body["started_at"] = start.replace(tzinfo=None).isoformat()
    assert api.client.post("/api/sessoes", headers=api.headers["manager"], json=body).status_code == 422
    body = payload(start, end, status="failed")
    assert api.client.post("/api/sessoes", headers=api.headers["manager"], json=body).status_code == 422


def test_tariff_versioning_and_impossible_windows(api):
    body = {"name": "Nova", "valid_from": "2027-01-01T00:00:00-03:00", "idle_fee_per_minute": "0.50",
            "overhead_percent": "5", "bands": [{"band": "off_peak", "green_price_per_kwh": "0.3",
                                                     "grid_price_per_kwh": "0.9"}]}
    response = api.client.post("/api/tarifas", headers=api.headers["manager"], json=body)
    assert response.status_code == 201, response.text
    versions = api.client.get("/api/tarifas", headers=api.headers["resident"]).json()
    assert len(versions) == 2 and versions[1]["valid_to"] is not None
    assert api.client.post("/api/tarifas", headers=api.headers["resident"], json=body).status_code == 403
    body.update(valid_from="2028-01-01T00:00:00-03:00", windows=[{
        "band": "peak", "start_time": "23:00", "end_time": "01:00"}])
    assert api.client.post("/api/tarifas", headers=api.headers["manager"], json=body).status_code == 422


def test_recommendation_identifies_estimation_and_uses_current_tariff(api):
    response = api.client.get("/api/recomendacao-janela", headers=api.headers["resident"],
                              params={"charger_id": api.charger.id, "kwh": "6.2", "power_kw": "3.3"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["model"] == "baseline-deterministico" and data["assumptions"]
    assert Decimal(data["predicted_cost"]) >= 0 and Decimal(data["savings"]) >= 0


def test_health_validates_database_migration_and_ai(api):
    result = api.client.get("/api/saude")
    assert result.status_code == 200 and result.json()["ai_model"] == "v1.0.0"
