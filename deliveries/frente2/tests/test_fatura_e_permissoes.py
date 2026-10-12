from decimal import Decimal

from tests.conftest import make_session, reserve


def _sessao_aprovada(client, resident):
    reserve(client, resident)
    assert client.post("/sessoes", json=make_session()).json()["processing_status"] == "Approved"


def test_fluxo_completo_sessao_ate_fatura(client, resident, manager):
    _sessao_aprovada(client, resident)
    r = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9})
    assert r.status_code == 200
    inv = r.json()[0]
    assert len(inv["items"]) == 1
    item = inv["items"][0]
    # sessao 19:00-21:10 cruza a faixa Ponta (ate 21:00) e a Fora de ponta
    assert [s["band"] for s in item["memory"]["segments"]] == ["Ponta", "Fora de ponta"]
    # parcelas presentes na fatura
    for campo in ("green_cost", "grid_cost", "idle_cost", "tax", "overhead", "total"):
        assert campo in item
    assert Decimal(item["total"]) == Decimal(item["subtotal"]) + Decimal(item["tax"]) + Decimal(item["overhead"])
    assert Decimal(inv["total"]) == Decimal(item["total"])


def test_fatura_nao_duplica_cobranca(client, resident, manager):
    _sessao_aprovada(client, resident)
    primeira = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()[0]
    segunda = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()
    assert len(segunda) == 1 and len(segunda[0]["items"]) == 1
    assert segunda[0]["total"] == primeira["total"]


def test_fatura_fechada_nao_muda(client, resident, manager):
    _sessao_aprovada(client, resident)
    inv = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()[0]
    assert client.post(f"/faturas/{inv['id']}/fechar", headers=manager).status_code == 200
    # sem sessao nova: devolve a fatura como esta
    same = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()[0]
    assert same["total"] == inv["total"] and same["status"] == "Closed"
    # com sessao nova aprovada no mesmo mes: recusa em vez de alterar em silencio
    reserve(client, resident, "2026-09-23T19:00:00", "2026-09-23T21:30:00")
    client.post("/sessoes", json=make_session(session_id="nova", started_at="2026-09-23T19:00:00",
                                              ended_at="2026-09-23T21:10:00"))
    again = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9})
    assert again.status_code == 409
    assert client.get(f"/faturas/{inv['id']}", headers=manager).json()["total"] == inv["total"]


def test_alterar_tarifa_atual_nao_muda_fatura_antiga(client, resident, manager):
    _sessao_aprovada(client, resident)
    inv = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()[0]
    total_antes = inv["total"]
    # nova versao da faixa Ponta, vigente a partir de outubro
    client.post("/tarifas", headers=manager, json={
        "name": "Ponta", "start_time": "18:00:00", "end_time": "21:00:00",
        "green_price": "9.9", "grid_price": "9.9", "valid_from": "2026-10-01"})
    depois = client.get(f"/faturas/{inv['id']}", headers=manager).json()
    assert depois["total"] == total_antes


def test_morador_ve_apenas_a_propria_fatura(client, resident, manager):
    _sessao_aprovada(client, resident)
    client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9})
    assert len(client.get("/faturas", headers=resident).json()) == 1


def test_relatorio_de_arrecadacao(client, resident, manager):
    _sessao_aprovada(client, resident)
    inv = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9}).json()[0]
    rel = client.get("/relatorios/arrecadacao", headers=manager, params={"year": 2026, "month": 9}).json()
    assert rel["total"] == inv["total"]


def test_sem_tarifa_configurada_avisa_em_vez_de_cobrar_errado(client, resident, manager, db):
    from models import Tariff
    db.query(Tariff).delete()
    db.commit()
    _sessao_aprovada(client, resident)
    r = client.post("/faturas/gerar", headers=manager, json={"year": 2026, "month": 9})
    assert r.status_code == 422


# ---- seguranca ----

def test_endpoints_do_gestor_recusam_morador(client, resident):
    assert client.get("/anomalias", headers=resident).status_code == 403
    assert client.post("/faturas/gerar", headers=resident, json={"year": 2026, "month": 9}).status_code == 403
    assert client.post("/tarifas", headers=resident, json={}).status_code == 403


def test_sem_token_e_401(client):
    assert client.get("/reservas").status_code == 401
    assert client.get("/faturas").status_code == 401


def test_login_invalido(client):
    r = client.post("/login", json={"email": "morador@demo.com", "password": "errada"})
    assert r.status_code == 401


def test_senha_e_guardada_como_hash(db):
    from models import User
    from sqlalchemy import select
    u = db.scalar(select(User).where(User.email == "morador@demo.com"))
    assert "morador-demo-123" not in u.password_hash and u.password_hash.startswith("pbkdf2_sha256$")


def test_cadastro_publico_sempre_cria_morador(client):
    r = client.post("/usuarios", json={"name": "Ana", "email": "ana@x.com", "password": "senha-forte-1", "unit_id": 1})
    assert r.status_code == 201 and r.json()["profile"] == "Morador"
    assert client.post("/usuarios", json={"name": "Ana", "email": "ana@x.com", "password": "senha-forte-1", "unit_id": 1}).status_code == 409


def test_recomendacao_de_janela(client, resident):
    r = client.get("/recomendacao-janela", headers=resident, params={"kwh": 20, "power_kw": 7})
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["predicted_cost"]) <= Decimal(body["cost_if_now"])
    assert body["recommended_start"]
