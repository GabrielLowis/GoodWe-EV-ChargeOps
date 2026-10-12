"""Conferência offline das coletas somente leitura; não conecta nem escreve no banco."""
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8-sig"))


checks = []


def check(name, condition, detail=None):
    checks.append({"criterion": name, "passed": bool(condition), "detail": detail})


before, after = read("db-before.json"), read("db-after.json")
b, a = before["tables"], after["tables"]
check("Ambas as transações PostgreSQL explicitamente somente leitura", before["transaction_read_only"] == after["transaction_read_only"] == "on")
changes, additions, removed = {}, {}, []
for table, rows in b.items():
    def rowkey(row):
        if table == "holidays":
            return row["holiday_date"]
        if table == "tariff_bands":
            return (row["tariff_id"], row["band"])
        return row["id"]
    old = {rowkey(r): r for r in rows}
    new = {rowkey(r): r for r in a[table]}
    additions[table] = [r for k, r in new.items() if k not in old]
    for k, row in old.items():
        if k not in new:
            removed.append([table, k])
        elif row != new[k]:
            changes.setdefault(table, {})[str(k)] = {field: {"before": row[field], "after": new[k][field]} for field in row if row[field] != new[k][field]}
check("Nenhum registro anterior excluído", not removed, removed)
check("Única atualização de registro anterior: reserva #3 active → no_show", changes == {"reservations": {"3": {"status": {"before": "active", "after": "no_show"}}}}, changes)
expected_counts = {"reservations": 1, "charging_sessions": 2, "anomalies": 2, "holidays": 1, "audit_events": 8}
check("Somente inclusões autorizadas", {t: len(v) for t, v in additions.items() if v} == expected_counts, {t: len(v) for t, v in additions.items() if v})
check("Faturas, itens e seus snapshots integralmente preservados", a["invoices"] == b["invoices"] and a["invoice_items"] == b["invoice_items"])
check("Reserva #1 e recarga #1 preservadas", a["reservations"][0] == b["reservations"][0] and a["charging_sessions"][0] == b["charging_sessions"][0])
check("Usuários, parâmetros e cadastro preservados; nenhum bloqueio", all(a[t] == b[t] for t in b if t not in expected_counts and t != "reservations"))
events = additions["audit_events"]
check("Oito eventos explicados; nenhuma geração/fechamento", Counter(r["action"] for r in events) == Counter({"no_show": 1, "reservation_created": 1, "anomaly_detected": 2, "session_ingested": 2, "anomaly_review": 1, "demo_holiday_added": 1}), [{"id": r["id"], "action": r["action"], "entity_id": r["entity_id"]} for r in events])
r = additions["reservations"][0]
check("Reserva #9, primeiro horário livre de amanhã, 09–10", r["id"] == 9 and r["user_id"] == 2 and r["status"] == "active" and r["starts_at"] == "2026-10-13T09:00:00-03:00" and r["ends_at"] == "2026-10-13T10:00:00-03:00" and not any(x["status"] in ("active", "in_use") and x["starts_at"] < r["ends_at"] and x["ends_at"] > r["starts_at"] for x in b["reservations"]))
sessions = additions["charging_sessions"]
for s in sessions:
    start, end, created = [datetime.fromisoformat(s[k]) for k in ("started_at", "ended_at", "created_at")]
    check(f"Sessão #{s['id']}: simulada, passada, órfã, zero, >=60s", s["source"] == "simulator" and s["user_id"] is None and s["reservation_id"] is None and s["end_status"] == "user_stopped" and end < created and (end-start).total_seconds() >= 60 and all(Decimal(s[k]) == 0 for k in ("total_kwh", "green_kwh", "grid_kwh", "average_power_kw", "max_power_kw")))
check("Dois identificadores fixos e sessões sem sobreposição", {s["external_id"] for s in sessions} == {"goal-overview-pendente-v1", "goal-overview-rejeitada-v1"} and sessions[1]["ended_at"] <= sessions[0]["started_at"])
anomalies = additions["anomalies"]
check("Pendente #1 permanece; rejeição #2 persistida pelo síndico", anomalies[0]["session_id"] == 2 and anomalies[0]["status"] == "pending_review" and anomalies[1]["session_id"] == 3 and anomalies[1]["status"] == "rejected" and anomalies[1]["reviewed_by"] == 1 and "simulada sem energia" in anomalies[1]["review_note"] and sessions[1]["validation_status"] == "rejected")
check("Nenhuma cobrança das novas sessões", not any(x["session_id"] in (2, 3) for x in a["invoice_items"]))
check("Feriado correto, único", a["holidays"] == [{"holiday_date": "2026-10-12", "description": "Feriado de demonstração acadêmica"}])
holiday = read("d05-executions.json")
check("Reexecução do feriado sem registros/eventos novos", holiday["first"]["created"] is True and holiday["second"]["created"] is False and holiday["after_first"] == holiday["after_second"] and holiday["after_second"]["holiday_audit_count"] == 1)
apib, apia = read("api-before.json"), read("api-after.json")
for role in ("resident", "manager"):
    check(f"{role}: detalhes integrais das faturas #1/#2 preservados", apia[role]["invoice_details"] == apib[role]["invoice_details"])
    check(f"{role}: detalhe recarga #1 preservado", next(s for s in apia[role]["session_details"] if s["id"] == 1) == next(s for s in apib[role]["session_details"] if s["id"] == 1))
check("Coleta final somente GET e login; todas respostas 200", all(q["status"] == 200 and (q["method"] == "GET" or q["path"] == "/login") for q in apia["requests"]))
report = apia["manager"]["reports"]["2026-10"]
check("Relatório mantém totais 4,04/6,2 e agrupa órfãs sem consumo", report["totals"] == apib["manager"]["reports"]["2026-10"]["totals"] and report["energy_balance"]["unattributed"] == {"count": 2, "kwh": "0.000", "session_ids": [2, 3]})
fb, fa = read("files-before.json"), read("files-after.json")
changed = [p for p in fb if fa.get(p) != fb[p]]
allowed = {"backend/api/routes.py", "backend/faturamento/service.py"}
check("Código anterior alterado apenas nas exceções API e frontend", all(p in allowed or p.startswith("frontend/src/") for p in changed), changed)
check("Contratos OpenAPI e cliente idênticos após regeneração", all(fb[p] == fa[p] for p in ("docs/openapi.json", "frontend/src/api/schema.d.ts")))
views = read("browser-checks.json")
check("44 capturas indexadas, sem transbordamento horizontal", len(views) == 44 and len({v["name"] for v in views}) == 44 and all(v["scrollWidth"] <= v["width"] for v in views))
check("Capturas desktop e 390px existentes", {390, 1280}.issubset({v["width"] for v in views}) and all((OUT/v.get("image_file", v["name"]+".jpg")).is_file() and (OUT/(v["name"]+".txt")).is_file() for v in views))
home = next(v for v in views if v["name"] == "25-morador-inicio-final")
check("Início mostra outubro R$4,04 e reserva #9", all(s in home["text"].replace("\u00a0", " ") for s in ("Fatura do mês", "outubro de 2026", "R$ 4,04", "Reserva #9")))
check("Console da conferência retomada sem erros/avisos", read("browser-console.json") == [])
check("Frontend: 50 testes aprovados", "50 passed (50)" in (OUT/"frontend-final-tests.txt").read_text(encoding="utf8"))
check("Backend: 150 aprovados sem pulados", "150 passed" in (OUT/"backend-final-tests.txt").read_text(encoding="utf8") and "skipped" not in (OUT/"backend-final-tests.txt").read_text(encoding="utf8"))
check("Build Vite e TypeScript aprovado", "built in" in (OUT/"frontend-final-build.txt").read_text(encoding="utf8"))
result = {"at": after["at"], "passed": all(c["passed"] for c in checks), "checks": checks, "modified_existing_files": changed, "new_files_in_tracked_scope": [p for p in fa if p not in fb]}
(OUT/"verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
print(json.dumps({"passed": result["passed"], "checks": len(checks), "failed": [c["criterion"] for c in checks if not c["passed"]]}, ensure_ascii=True))
raise SystemExit(0 if result["passed"] else 1)
