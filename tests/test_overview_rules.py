from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import func, select
from backend.api import routes
from backend.db.models import AuditEvent, Reservation
from backend.faturamento import service as billing

pytestmark = pytest.mark.db


@pytest.mark.parametrize("role", ["resident", "manager"])
@pytest.mark.parametrize("offset", [-1, 0, 1, 3600])
def test_cancel_only_before_start_and_no_write_when_denied(api, monkeypatch, role, offset):
    start = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)
    response = api.client.post("/api/reservas", headers=api.headers["resident"], json={
        "charger_id": api.charger.id, "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=1)).isoformat()})
    assert response.status_code == 201
    reservation_id = response.json()["id"]
    count = api.db.scalar(select(func.count()).select_from(AuditEvent))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return start + timedelta(seconds=offset)

    monkeypatch.setattr(routes, "datetime", Clock)
    result = api.client.post(f"/api/reservas/{reservation_id}/cancelar", headers=api.headers[role])
    row = api.db.get(Reservation, reservation_id)
    api.db.refresh(row)
    if offset < 0:
        assert result.status_code == 200
        assert row.status == "cancelled" and row.cancelled_at is not None
    else:
        assert result.status_code == 409
        assert "antes do início" in result.json()["detail"]
        assert row.status == "active" and row.cancelled_at is None
        assert api.db.scalar(select(func.count()).select_from(AuditEvent)) == count


@pytest.mark.parametrize("before_end", [3600, 0.000001, 0, -1])
def test_closing_local_month_boundary_and_idempotence(api, monkeypatch, before_end):
    result = api.client.post('/api/faturas/gerar', headers=api.headers['manager'], json={
        'year': 2026, 'month': 10, 'user_id': api.resident.id})
    assert result.status_code == 200
    invoice = result.json()[0]
    invoice_id = invoice['id']
    count = api.db.scalar(select(func.count()).select_from(AuditEvent))
    clock = datetime(2026, 11, 1, 3, tzinfo=UTC) - timedelta(seconds=before_end)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock

    monkeypatch.setattr(billing, 'datetime', Clock)
    response = api.client.post(f'/api/faturas/{invoice_id}/fechar', headers=api.headers['manager'])
    if before_end > 0:
        assert response.status_code == 409
        assert '01/11/2026 00:00' in response.json()['detail']
        assert api.client.get(f'/api/faturas/{invoice_id}', headers=api.headers['manager']).json() == invoice
        assert api.db.scalar(select(func.count()).select_from(AuditEvent)) == count
    else:
        assert response.status_code == 200 and response.json()['status'] == 'closed'
        closed = response.json()
        clock = datetime(2026, 10, 12, tzinfo=UTC)
        again = api.client.post(f'/api/faturas/{invoice_id}/fechar', headers=api.headers['manager'])
        assert again.status_code == 200 and again.json() == closed
        assert api.db.scalar(select(func.count()).select_from(AuditEvent)) == count + 1
