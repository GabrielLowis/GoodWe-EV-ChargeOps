"""Diagnóstico local: GETs e SELECTs em transação READ ONLY; nunca altera domínio."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend import config
from backend.db.base import Base, make_engine
from backend.db import models
from backend.faturamento import repository as repo
from backend.faturamento.mappers import session_to_input, tariff_to_spec, tax_rule_to_spec
from backend.rateio import calculate_session, summarize_invoice
from dotenv import dotenv_values

OUT = Path(__file__).resolve().parent
SECRET_KEYS = {"password", "password_hash", "access_token", "jwt_secret", "authorization", "card_id"}


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k.lower() not in SECRET_KEYS}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(config.CONDO_TIMEZONE).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def canonical(value):
    return json.dumps(value, default=str, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write(name, data):
    (OUT / name).write_text(json.dumps(clean(data), default=str, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files():
    roots = ["backend", "condocharge_ai", "scripts", "infra", "data", "deliveries", "frontend/src", "docs"]
    paths = [ROOT / p for p in ("README.md", "AGENTS.md", "frontend/package.json", "frontend/package-lock.json")]
    for root in roots:
        paths.extend((ROOT / root).rglob("*"))
    return {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def database(stage):
    engine = make_engine()
    now = datetime.now(UTC)
    with engine.connect() as conn:
        transaction = conn.begin()
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        mode = conn.scalar(text("SHOW transaction_read_only"))
        assert mode == "on"
        tables, hashes, counts = {}, {}, {}
        for table in Base.metadata.sorted_tables:
            rows = [dict(r) for r in conn.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
            tables[table.name] = rows
            hashes[table.name] = hashlib.sha256(canonical(rows).encode()).hexdigest()
            counts[table.name] = len(rows)
        write(f"db-{stage}.json", {"at": now, "transaction_read_only": mode, "counts": counts,
                                   "table_sha256": hashes, "tables": tables})
        if stage == "before":
            db = Session(bind=conn, autoflush=False)
            checks = {"at": now, "transaction_read_only": mode}
            reservations = list(db.scalars(select(models.Reservation)))
            sessions = list(db.scalars(select(models.ChargingSession)))
            invoices = list(db.scalars(select(models.Invoice)))
            items = list(db.scalars(select(models.InvoiceItem)))
            rmap = {r.id: r for r in reservations}
            smap = {s.id: s for s in sessions}
            imap = {i.id: i for i in invoices}
            checks["expired_active_reservations"] = [r.id for r in reservations if r.status == "active" and r.ends_at <= now]
            checks["started_active_reservations"] = [r.id for r in reservations if r.status == "active" and r.starts_at <= now]
            checks["completed_without_session"] = [r.id for r in reservations if r.status == "completed" and not any(s.reservation_id == r.id for s in sessions)]
            checks["completed_future_sessions"] = [s.id for s in sessions if s.end_status != "in_progress" and s.ended_at and s.ended_at > now]
            checks["orphan_sessions"] = [s.id for s in sessions if s.user_id is None]
            checks["duplicate_invoice_sessions"] = [sid for sid, count in Counter(i.session_id for i in items).items() if count > 1]
            checks["link_issues"] = []
            for s in sessions:
                r = rmap.get(s.reservation_id)
                if s.reservation_id and (not r or s.user_id != r.user_id or s.charger_id != r.charger_id or s.connector != r.connector or not r.starts_at <= s.started_at < r.ends_at):
                    checks["link_issues"].append({"session_id": s.id, "reservation_id": s.reservation_id})
            for item in items:
                if item.user_id != smap[item.session_id].user_id or item.user_id != imap[item.invoice_id].user_id:
                    checks["link_issues"].append({"item_id": item.id})
            checks["unbilled_sessions"] = [{"session_id": s.id, "user_id": s.user_id, "validation_status": s.validation_status,
                                             "end_status": s.end_status, "started_at": s.started_at}
                                            for s in sessions if not any(i.session_id == s.id for i in items)]
            checks["energy_mismatch"] = [s.id for s in sessions if abs(s.total_kwh-s.green_kwh-s.grid_kwh) > Decimal("0.05")]
            candidates = [r for r in reservations if r.status == "active" and r.starts_at < now-timedelta(minutes=20)]
            checks["no_show_dry_inspection"] = {"would_mark_ids": [r.id for r in candidates],
                "would_block_user_ids": sorted({r.user_id for r in candidates if sum(1 for q in reservations if q.user_id == r.user_id and q.starts_at >= now-timedelta(days=30) and (q.status == "no_show" or q in candidates)) >= 3}),
                "note": "Inspeção pura da condição atual; endpoint não chamado."}
            fields = ("green_amount", "grid_amount", "idle_amount", "subtotal", "tax_amount", "overhead_amount", "total", "green_kwh", "grid_kwh", "idle_minutes")
            checks["invoice_aggregation"] = []
            checks["engine_recomputation"] = []
            holidays = repo.all_holidays(db)
            for inv in invoices:
                own = [i for i in items if i.invoice_id == inv.id]
                differences = {f: {"invoice": getattr(inv, f), "items_sum": sum((getattr(i, f) for i in own), Decimal(0))}
                               for f in fields if getattr(inv, f) != sum((getattr(i, f) for i in own), Decimal(0))}
                if inv.sessions_count != len(own):
                    differences["sessions_count"] = {"invoice": inv.sessions_count, "items_count": len(own)}
                checks["invoice_aggregation"].append({"invoice_id": inv.id, "differences": differences})
            for item in items:
                session = smap[item.session_id]
                tariff = db.get(models.Tariff, item.tariff_id)
                taxes = [tax_rule_to_spec(t) for t in repo.tax_rules_at(db, session.started_at, config.TAX_JURISDICTION)]
                charge = calculate_session(session_to_input(session), tariff_to_spec(tariff), taxes, holidays, config.CONDO_TIMEZONE)
                differences = {f: {"persisted": getattr(item, f), "engine": getattr(charge, f)} for f in fields if getattr(item, f) != getattr(charge, f)}
                checks["engine_recomputation"].append({"item_id": item.id, "session_id": session.id, "invoice_id": item.invoice_id,
                                                         "tariff_id": item.tariff_id, "differences": differences,
                                                         "calculation": charge.calculation})
            write("cross-checks.json", checks)
            db.close()
        transaction.rollback()
    engine.dispose()
    return hashes


def api(stage):
    env = dotenv_values(ROOT / ".env")
    password = env.get("DEMO_PASSWORD")
    assert password, "DEMO_PASSWORD ausente; nenhum segredo registrado"
    data = {"at": datetime.now(UTC), "requests": []}
    with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=20) as client:
        def get(path, params=None):
            result = client.get(path, params=params)
            data["requests"].append({"method": "GET", "path": path, "params": params, "status": result.status_code})
            result.raise_for_status()
            return result.json()
        data["health"] = get("/saude")
        for role, email in (("resident", "morador@demo.local"), ("manager", "sindico@demo.local")):
            response = client.post("/login", json={"email": email, "password": password})
            data["requests"].append({"method": "POST", "path": "/login", "role": role, "status": response.status_code})
            response.raise_for_status()
            client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
            account = data[role] = {"user": get("/usuarios/eu")}
            for path in ("unidades", "carregadores", "reservas", "sessoes", "faturas", "tarifas"):
                account[path] = get("/"+path)
            account["session_details"] = [get(f"/sessoes/{s['id']}") for s in account["sessoes"]]
            account["invoice_details"] = [get(f"/faturas/{i['id']}") for i in account["faturas"]]
            if role == "manager":
                account["usuarios"] = get("/usuarios")
                account["impostos"] = get("/impostos")
                account["anomalias"] = {status: get("/anomalias", {"status": status}) for status in ("pending_review", "approved", "rejected")}
                periods = {i["period"][:7] for i in account["faturas"]} | {s["started_at"][:7] for s in account["sessoes"]} | {datetime.now(config.CONDO_TIMEZONE).strftime("%Y-%m")}
                account["reports"] = {p: get("/relatorios/arrecadacao", {"year": int(p[:4]), "month": int(p[5:])}) for p in sorted(periods)}
            else:
                charger = next((c for c in account["carregadores"] if c["active"]), None)
                if stage == "before" and charger:
                    account["recommendation"] = get("/recomendacao-janela", {"charger_id": charger["id"], "kwh": "6.2", "power_kw": "3.3"})
                account["availability"] = []
                for r in account["reservas"]:
                    account["availability"].append({"reservation_id": r["id"], "result": get(f"/carregadores/{r['charger_id']}/disponibilidade", {"start": r["starts_at"], "end": r["ends_at"]})})
        client.headers.pop("Authorization", None)
    write(f"api-{stage}.json", data)
    return data


def run(stage):
    OUT.mkdir(parents=True, exist_ok=True)
    write(f"files-{stage}.json", files())
    hashes = database(stage)
    response = api(stage)
    if stage == "after":
        prior = json.loads((OUT / "db-before.json").read_text(encoding="utf-8"))["table_sha256"]
        earlier = json.loads((OUT / "files-before.json").read_text(encoding="utf-8"))
        current = files()
        write("preservation.json", {"at": datetime.now(UTC), "database_tables_changed": [k for k in hashes if hashes[k] != prior.get(k)],
             "protected_files_changed": [k for k in current if current[k] != earlier.get(k)],
             "protected_files_removed": sorted(set(earlier)-set(current)), "protected_files_count": len(current),
             "domain_post_requests": [r for r in response["requests"] if r["method"] != "GET" and r["path"] != "/login"]})
    print(json.dumps({"stage": stage, "tables": len(hashes), "requests": len(response["requests"]), "evidence": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("before", "after")
    run(sys.argv[1])
