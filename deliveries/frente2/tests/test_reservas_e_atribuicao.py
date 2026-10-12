import datetime

from models import AuditEvent, Reservation, ReservationStatus
from services.reservations import process_no_shows
from sqlalchemy import select
from tests.conftest import make_session, reserve


def test_cria_reserva_valida(client, resident):
    r = reserve(client, resident)
    assert r.status_code == 201
    assert r.json()["status"] == "Await"


def test_impede_duas_reservas_incompativeis_no_mesmo_carregador(client, resident, manager):
    assert reserve(client, resident).status_code == 201
    outra = reserve(client, manager, start="2026-09-22T20:00:00", end="2026-09-22T22:00:00")
    assert outra.status_code == 409


def test_reservas_em_horarios_diferentes_convivem(client, resident):
    assert reserve(client, resident, "2026-09-22T10:00:00", "2026-09-22T11:00:00").status_code == 201
    assert reserve(client, resident, "2026-09-22T11:00:00", "2026-09-22T12:00:00").status_code == 201


def test_capacidade_simultanea_parametrizada(client, resident, manager, monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_RESERVATIONS", "2")
    assert reserve(client, resident).status_code == 201
    assert reserve(client, manager).status_code == 201
    assert reserve(client, resident).status_code == 409


def test_reserva_com_fim_antes_do_inicio_e_recusada(client, resident):
    assert reserve(client, resident, "2026-09-22T21:00:00", "2026-09-22T20:00:00").status_code == 422


def test_cancelar_libera_a_janela(client, resident, manager):
    rid = reserve(client, resident).json()["id"]
    assert client.post(f"/reservas/{rid}/cancelar", headers=resident).status_code == 200
    assert reserve(client, manager).status_code == 201


def test_morador_nao_cancela_reserva_de_outro(client, resident, manager):
    rid = reserve(client, manager).json()["id"]
    assert client.post(f"/reservas/{rid}/cancelar", headers=resident).status_code == 403


def test_sessao_e_atribuida_ao_morador_da_reserva_correta(client, resident, manager):
    me = client.get("/usuarios/eu", headers=resident).json()
    rid = reserve(client, resident).json()["id"]
    r = client.post("/sessoes", json=make_session())
    assert r.status_code == 201
    body = r.json()
    assert body["reservation_id"] == rid
    assert body["user_id"] == me["id"]
    assert body["processing_status"] == "Approved"


def test_sessao_sem_reserva_vira_orfa_e_vai_para_o_sindico(client, manager):
    body = client.post("/sessoes", json=make_session()).json()
    assert body["user_id"] is None
    assert body["processing_status"] == "Orphan"
    assert body["reasons"][0]["code"] == "ORPHAN_SESSION"
    fila = client.get("/anomalias", headers=manager).json()
    assert len(fila) == 1 and fila[0]["session_id"] == "abc123"


def test_reserva_nao_e_reaproveitada_por_segunda_sessao(client, resident):
    reserve(client, resident)
    client.post("/sessoes", json=make_session())
    segunda = client.post("/sessoes", json=make_session(session_id="outra"))
    assert segunda.json()["processing_status"] == "Orphan"


def test_sessao_duplicada_e_recusada(client):
    assert client.post("/sessoes", json=make_session()).status_code == 201
    assert client.post("/sessoes", json=make_session()).status_code == 409


def test_carregador_inexistente_e_recusado(client):
    assert client.post("/sessoes", json=make_session(charger_id="XYZ")).status_code == 422


def test_no_show_apos_20_minutos_e_reincidencia(client, resident, db):
    rid = reserve(client, resident, "2026-09-22T19:00:00", "2026-09-22T21:00:00").json()["id"]
    # 19 minutos depois: ainda vale
    assert process_no_shows(db, datetime.datetime(2026, 9, 22, 19, 19)) == []
    # 21 minutos depois: no-show
    done = process_no_shows(db, datetime.datetime(2026, 9, 22, 19, 21))
    assert done[0]["reservation_id"] == rid and done[0]["no_shows_total"] == 1
    assert db.get(Reservation, rid).status == ReservationStatus.No_show

    reserve(client, resident, "2026-09-23T19:00:00", "2026-09-23T21:00:00")
    done = process_no_shows(db, datetime.datetime(2026, 9, 23, 20, 0))
    assert done[0]["no_shows_total"] == 2
    events = db.scalars(select(AuditEvent).where(AuditEvent.event_type == "NO_SHOW")).all()
    assert len(events) == 2
