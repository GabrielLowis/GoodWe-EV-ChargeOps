"""Cenários D04 autorizados: no máximo uma reserva e dois external_ids fixos."""
import json
import sys
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
assert ROOT == Path('C:/Users/Gabriel Luis/Documents/ChatGPT/GoodWe').resolve()
OUT = Path(__file__).resolve().parent
MANIFEST = OUT / 'scenario-manifest.json'
TZ = ZoneInfo('America/Sao_Paulo')


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def save(data):
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'created_at': datetime.now(TZ).isoformat(), 'sessions': {}, 'requests': []}
    password = dotenv_values(ROOT / '.env')['DEMO_PASSWORD']
    with httpx.Client(base_url='http://127.0.0.1:8000/api', timeout=20) as resident, httpx.Client(base_url='http://127.0.0.1:8000/api', timeout=20) as manager:
        for client, email in ((resident, 'morador@demo.local'), (manager, 'sindico@demo.local')):
            result = client.post('/login', json={'email': email, 'password': password})
            result.raise_for_status()
            client.headers['Authorization'] = 'Bearer ' + result.json()['access_token']

        def call(client, method, path, **kwargs):
            result = client.request(method, path, **kwargs)
            manifest['requests'].append({'at': datetime.now(TZ).isoformat(), 'method': method, 'path': path, 'status': result.status_code})
            save(manifest)
            result.raise_for_status()
            return result.json()

        user = call(resident, 'GET', '/usuarios/eu')
        assert user['id'] == 2 and user['role'] == 'resident' and user['reservation_blocked_until'] is None
        chargers = call(manager, 'GET', '/carregadores')
        charger = next(c for c in chargers if c['code'] == 'HCA01')
        assert charger['active'] and Decimal(charger['rated_power_kw']) == 7
        reservations = call(manager, 'GET', '/reservas')
        now = datetime.now(TZ)
        tomorrow = now.date() + timedelta(days=1)
        if 'reservation_id' in manifest:
            row = next(r for r in reservations if r['id'] == manifest['reservation_id'])
            assert row['status'] == 'active' and timestamp(row['starts_at']) > now, 'Reserva já preparada alterada/vencida; não criar substituta automaticamente'
        else:
            plan = manifest.get('reservation_plan')
            if not plan:
                for hour in range(9, 18):
                    start = datetime.combine(tomorrow, time(hour), TZ)
                    end = start + timedelta(hours=1)
                    available = call(resident, 'GET', f"/carregadores/{charger['id']}/disponibilidade", params={'start': start.isoformat(), 'end': end.isoformat()})
                    if not any(r['connector'] == 1 for r in available['busy']):
                        plan = {'charger_id': charger['id'], 'connector': 1, 'starts_at': start.isoformat(), 'ends_at': end.isoformat()}
                        break
                assert plan, 'Nenhuma janela livre entre 09 e 18; não ampliar a busca'
                manifest['reservation_plan'] = plan
                save(manifest)
            # Recupera resultado de eventual POST interrompido, sem criar outro registro.
            matching = [r for r in reservations if r['user_id'] == user['id'] and r['charger_id'] == plan['charger_id'] and r['connector'] == 1 and timestamp(r['starts_at']) == timestamp(plan['starts_at']) and timestamp(r['ends_at']) == timestamp(plan['ends_at']) and r['status'] == 'active']
            assert len(matching) <= 1
            row = matching[0] if matching else call(resident, 'POST', '/reservas', json=plan)
            manifest['reservation_id'] = row['id']
            manifest['reservation'] = row
            save(manifest)

        all_sessions = call(manager, 'GET', '/sessoes')
        anomalies = []
        for status in ('pending_review', 'approved', 'rejected'):
            anomalies.extend(call(manager, 'GET', '/anomalias', params={'status': status}))
        for position, external in enumerate(('goal-overview-pendente-v1', 'goal-overview-rejeitada-v1')):
            existing = [s for s in all_sessions if s['external_id'] == external]
            assert len(existing) <= 1
            if existing:
                session = existing[0]
                assert session['source'] == 'simulator' and session['end_status'] == 'user_stopped' and session['user_id'] is None and session['reservation_id'] is None
                assert all(Decimal(session[k]) == 0 for k in ('total_kwh', 'green_kwh', 'grid_kwh', 'average_power_kw', 'max_power_kw'))
                assert timestamp(session['ended_at']) <= datetime.now(UTC) and timestamp(session['ended_at']) - timestamp(session['started_at']) >= timedelta(seconds=60)
                anomaly = next(a for a in anomalies if a['session_id'] == session['id'])
                assert anomaly['status'] in (('pending_review',) if position == 0 else ('pending_review', 'rejected'))
                manifest['sessions'].setdefault(external, {}).update(session_id=session['id'], anomaly_id=anomaly['id'], state=anomaly['status'], reused=True)
                save(manifest)
                continue
            payload = manifest['sessions'].get(external, {}).get('payload')
            if not payload:
                for attempt in range(20):
                    start = (datetime.now(UTC) - timedelta(minutes=10 + position*3 + attempt*5)).replace(microsecond=0)
                    end = start + timedelta(minutes=1)
                    overlaps = any(s['charger_id'] == charger['id'] and s['connector'] == 1 and s['ended_at'] and timestamp(s['started_at']) < end and timestamp(s['ended_at']) > start for s in all_sessions)
                    attributed = any(r['charger_id'] == charger['id'] and r['connector'] == 1 and r['status'] in ('active', 'in_use') and timestamp(r['starts_at']) <= start < timestamp(r['ends_at']) for r in reservations)
                    if not overlaps and not attributed:
                        break
                else:
                    raise RuntimeError('Sem intervalo passado adequado nas 20 opções; não criar cenário alternativo')
                payload = {'source': 'simulator', 'session_id': external, 'charger_id': charger['code'], 'connector': 1, 'started_at': start.isoformat(), 'ended_at': end.isoformat(), 'energy_ended_at': end.isoformat(), 'total_kwh': '0.000', 'green_kwh': '0.000', 'grid_kwh': '0.000', 'average_power_kw': '0.00', 'max_power_kw': '0.00', 'status': 'user_stopped'}
                manifest['sessions'][external] = {'payload': payload}
                save(manifest)
            result = call(manager, 'POST', '/sessoes', json=payload)
            session = result['session']
            assert result['anomaly_id'] is not None and session['validation_status'] == 'suspended' and session['user_id'] is None and session['reservation_id'] is None
            assert 'NO_ENERGY_DELIVERED' in result['detection']['reasons'] and 'ORPHAN_SESSION' in result['detection']['reasons']
            manifest['sessions'][external].update(session_id=session['id'], anomaly_id=result['anomaly_id'], state='pending_review', result=result)
            all_sessions.append(session)
            save(manifest)
        print(json.dumps({'reservation_id': manifest['reservation_id'], 'sessions': {k: {'session_id': v['session_id'], 'anomaly_id': v['anomaly_id']} for k,v in manifest['sessions'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
