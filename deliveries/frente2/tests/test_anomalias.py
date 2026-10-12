from tests.conftest import make_session, reserve


def test_sessao_normal_com_reserva_segue_para_o_rateio(client, resident):
    reserve(client, resident)
    body = client.post("/sessoes", json=make_session()).json()
    assert body["processing_status"] == "Approved"
    assert body["anomaly_id"] is None


def test_sessao_fisicamente_impossivel_e_bloqueada_antes_da_fatura(client, resident, manager):
    reserve(client, resident)
    # 14,8 kWh em 20 min com 7,1 kW de potencia maxima: impossivel
    s = make_session(ended_at="2026-09-22T19:20:00", average_power_kw=7.0)
    body = client.post("/sessoes", json=s).json()
    assert body["processing_status"] == "Suspended"
    assert body["reasons"][0]["code"] == "PHYSICAL_IMPOSSIBLE"
    fila = client.get("/anomalias", headers=manager).json()
    assert fila[0]["layer_failed"] == 2


def test_potencia_acima_do_limite_do_carregador(client, resident):
    reserve(client, resident)
    body = client.post("/sessoes", json=make_session(max_power_kw=60.0)).json()
    assert body["processing_status"] == "Suspended"
    assert "EXCEEDS_CHARGER_POWER" in [r["code"] for r in body["reasons"]]


def test_camada_1_energia_nao_fecha(client, resident):
    reserve(client, resident)
    body = client.post("/sessoes", json=make_session(green_kwh=1.0, grid_kwh=1.0)).json()
    assert body["processing_status"] == "Suspended"
    assert body["reasons"][0]["code"] == "ENERGY_MISMATCH"


def test_tempo_inconsistente_para_na_camada_1(client, resident, manager):
    reserve(client, resident)
    body = client.post("/sessoes", json=make_session(ended_at="2026-09-22T18:00:00")).json()
    assert body["processing_status"] == "Suspended"
    assert client.get("/anomalias", headers=manager).json()[0]["layer_failed"] == 1


def test_sindico_aprova_e_deixa_trilha_de_auditoria(client, resident, manager, db):
    from models import AuditEvent
    from sqlalchemy import select
    reserve(client, resident)
    aid = client.post("/sessoes", json=make_session(max_power_kw=60.0)).json()["anomaly_id"]
    r = client.post(f"/anomalias/{aid}/revisao", headers=manager, json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "Approved"
    assert client.get("/sessoes/abc123", headers=manager).json()["processing_status"] == "Approved"
    ev = db.scalars(select(AuditEvent).where(AuditEvent.event_type == "ANOMALY_REVIEWED")).all()
    assert len(ev) == 1
    # revisar de novo nao e permitido
    assert client.post(f"/anomalias/{aid}/revisao", headers=manager, json={"decision": "reject"}).status_code == 409


def test_sindico_rejeita_e_sessao_nao_e_cobrada(client, resident, manager):
    reserve(client, resident)
    aid = client.post("/sessoes", json=make_session(max_power_kw=60.0)).json()["anomaly_id"]
    client.post(f"/anomalias/{aid}/revisao", headers=manager, json={"decision": "reject"})
    assert client.get("/sessoes/abc123", headers=manager).json()["processing_status"] == "Rejected"
    assert client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json() == []


def test_orfa_so_e_aprovada_com_morador_indicado(client, resident, manager):
    aid = client.post("/sessoes", json=make_session()).json()["anomaly_id"]
    assert client.post(f"/anomalias/{aid}/revisao", headers=manager,
                       json={"decision": "approve"}).status_code == 422
    uid = client.get("/usuarios/eu", headers=resident).json()["id"]
    ok = client.post(f"/anomalias/{aid}/revisao", headers=manager, json={"decision": "approve", "user_id": uid})
    assert ok.status_code == 200
    assert client.get("/sessoes/abc123", headers=manager).json()["user_id"] == uid
