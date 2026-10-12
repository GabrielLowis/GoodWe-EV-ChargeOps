from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import func, select
from backend.db.models import AuditEvent, Holiday
from backend.faturamento.repository import all_holidays
from backend.rateio import calculate_session
from backend.rateio.models import SessionInput
from scripts.register_demo_holiday import HOLIDAY_DATE, register_demo_holiday, require_local_demo_database
from backend.tests.helpers import build_tariff


@pytest.mark.parametrize('url', [
    'postgresql+psycopg://u:p@external.example/evchargeops',
    'postgresql+psycopg://u:p@127.0.0.1/evchargeops_test',
    'postgresql+psycopg://u:p@127.0.0.1/another',
    'sqlite:///evchargeops',
])
def test_script_refuses_any_other_database(url):
    with pytest.raises(ValueError, match='PostgreSQL local'):
        require_local_demo_database(url)


@pytest.mark.db
def test_holiday_inclusion_is_idempotent_and_engine_uses_off_peak(api):
    tariff = build_tariff()
    first = register_demo_holiday(api.db, api.manager.id)
    second = register_demo_holiday(api.db, api.manager.id)
    assert first['created'] is True and second['created'] is False
    assert api.db.scalar(select(func.count()).select_from(Holiday)) == 1
    assert api.db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'demo_holiday_added')) == 1
    start = datetime(2026, 10, 12, 18, tzinfo=ZoneInfo('America/Sao_Paulo'))
    charge = calculate_session(SessionInput(session_id=1, user_id=api.resident.id, started_at=start, ended_at=start+timedelta(hours=1), energy_ended_at=start+timedelta(hours=1), total_kwh=Decimal('1'), green_kwh=Decimal('0'), grid_kwh=Decimal('1'), end_status='completed', validation_status='approved', charger_rated_power_kw=Decimal('7')), tariff, [], all_holidays(api.db), ZoneInfo('America/Sao_Paulo'))
    assert all(s['band'] == 'off_peak' for s in charge.calculation['band_split']['segments'])


@pytest.mark.db
def test_existing_holiday_is_preserved_without_new_audit(api):
    api.db.add(Holiday(holiday_date=HOLIDAY_DATE, description='Cadastro anterior preservado'))
    api.db.flush()
    result = register_demo_holiday(api.db, api.manager.id)
    assert result == {'created': False, 'holiday_date': '2026-10-12', 'description': 'Cadastro anterior preservado'}
    assert api.db.scalar(select(func.count()).select_from(AuditEvent)) == 0
