"""Demonstração HTTP real: reserva -> sessão simulada -> IA/revisão -> fatura."""
import os
from datetime import datetime, UTC, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo
import httpx
from dotenv import load_dotenv

load_dotenv()
base = os.getenv("API_URL", "http://localhost:8000/api")
password = os.environ["DEMO_PASSWORD"]


def call(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


with httpx.Client(base_url=base, timeout=30) as manager, httpx.Client(base_url=base, timeout=30) as resident:
    for client, email in [(manager, "sindico@demo.local"), (resident, "morador@demo.local")]:
        token = call(client, "POST", "/login", json={"email": email, "password": password})["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    user = call(resident, "GET", "/usuarios/eu")
    charger = next(c for c in call(resident, "GET", "/carregadores") if c["code"] == "HCA01")
    # Avança para a primeira janela sem conflito; timestamps futuros deixam explícita a aceleração da demo.
    start = datetime.now(UTC) + timedelta(hours=1)
    for _ in range(168):
        busy = call(resident, "GET", f"/carregadores/{charger['id']}/disponibilidade",
                    params={"start": start.isoformat(), "end": (start+timedelta(hours=3)).isoformat()})["busy"]
        if not busy:
            break
        start += timedelta(hours=3)
    else:
        raise RuntimeError("Sem janela livre para demo")
    end = start + timedelta(hours=3)
    reservation = call(resident, "POST", "/reservas", json={"charger_id": charger["id"],
                        "starts_at": start.isoformat(), "ends_at": end.isoformat(), "connector": 1})
    # Sessão de três horas, ~2,3 kW médios e 3,3 kW de pico (regime do dataset da Frente 4).
    session = call(manager, "POST", "/sessoes", json={
        "source": "simulator", "session_id": "demo-" + uuid4().hex, "charger_id": charger["code"],
        "card_id": "SHARED-DEMO", "started_at": start.isoformat(), "ended_at": end.isoformat(),
        "energy_ended_at": end.isoformat(), "total_kwh": "6.200", "green_kwh": "1.000", "grid_kwh": "5.200",
        "average_power_kw": "2.30", "max_power_kw": "3.30", "status": "completed"})
    if session["anomaly_id"]:
        call(manager, "POST", f"/anomalias/{session['anomaly_id']}/revisao",
             json={"decision": "approve", "note": "Demonstração controlada com dados simulados."})
    local_start = start.astimezone(ZoneInfo(os.getenv("CONDO_TIMEZONE", "America/Sao_Paulo")))
    invoices = call(manager, "POST", "/faturas/gerar", json={"year": local_start.year, "month": local_start.month,
                                                           "user_id": user["id"]})
    invoice = invoices[0]
    if not any(i["session_id"] == session["session"]["id"] for i in invoice["items"]):
        raise RuntimeError("Sessão não entrou na fatura; conferir calculation.not_included")
    print(f"SIMULAÇÃO: reserva {reservation['id']}, sessão {session['session']['id']}, "
          f"fatura {invoice['id']}, total R$ {invoice['total']}; sem GoodWe real.")
