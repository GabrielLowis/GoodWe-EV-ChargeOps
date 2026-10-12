"""Compara exclusivamente os JSONs sanitizados já coletados."""
import json
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent
db = json.loads((OUT / "db-before.json").read_text(encoding="utf-8"))
api = json.loads((OUT / "api-before.json").read_text(encoding="utf-8"))
tables = db["tables"]


def normal(value):
    if isinstance(value, dict):
        return {k: normal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normal(v) for v in value]
    if isinstance(value, str):
        if re.fullmatch(r"\d{4}-\d\d-\d\dT.+(?:Z|[+-]\d\d:\d\d)", value):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
            return Decimal(value)
    return value


comparisons, mismatches = [], []
mapping = {"user": "users", "unidades": "condo_units", "carregadores": "chargers", "reservas": "reservations",
           "sessoes": "charging_sessions", "faturas": "invoices", "tarifas": "tariffs", "usuarios": "users", "impostos": "tax_rules"}
for role in ("resident", "manager"):
    for key, table in mapping.items():
        if key not in api[role]:
            continue
        rows = [api[role][key]] if key == "user" else api[role][key]
        source = {r["id"]: r for r in tables[table]}
        for row in rows:
            differences = [k for k, value in row.items() if k in source[row["id"]] and normal(value) != normal(source[row["id"]][k])]
            entry = {"role": role, "collection": key, "id": row["id"], "differences": differences}
            comparisons.append(entry)
            if differences:
                mismatches.append(entry)
            if key == "faturas":
                expected_ids = sorted(r["id"] for r in tables["invoice_items"] if r["invoice_id"] == row["id"])
                actual_ids = sorted(r["id"] for r in row["items"])
                if expected_ids != actual_ids:
                    mismatches.append({"role": role, "invoice_id": row["id"], "expected_items": expected_ids, "api_items": actual_ids})

trace = []
for reservation in tables["reservations"]:
    sessions = [s for s in tables["charging_sessions"] if s["reservation_id"] == reservation["id"]]
    items = [i for i in tables["invoice_items"] if i["session_id"] in [s["id"] for s in sessions]]
    trace.append({"user_id": reservation["user_id"], "reservation_id": reservation["id"], "reservation_status": reservation["status"],
                  "starts_at": reservation["starts_at"], "ends_at": reservation["ends_at"], "session_ids": [s["id"] for s in sessions],
                  "item_ids": [i["id"] for i in items], "invoice_ids": sorted({i["invoice_id"] for i in items})})

reports = []
money = ("green_amount", "grid_amount", "idle_amount", "subtotal", "tax_amount", "overhead_amount", "total")
for period, report in api["manager"]["reports"].items():
    invoices = [i for i in tables["invoices"] if i["period"].startswith(period)]
    differences = [field for field in money if Decimal(report["totals"][field]) != sum((Decimal(i[field]) for i in invoices), Decimal(0))]
    reports.append({"period": period, "differences": differences, "invoices_count_matches": report["totals"]["invoices_count"] == len(invoices)})

now = datetime.fromisoformat(db["at"])
chronology = {"future_invoice_ids": [i["id"] for i in tables["invoices"] if i["period"][:7] > now.strftime("%Y-%m")],
              "invoices_closed_before_period_end": [i["id"] for i in tables["invoices"] if i["closed_at"] and datetime.fromisoformat(i["closed_at"]).strftime("%Y-%m") <= i["period"][:7]],
              "sessions_ingested_before_started_at": [s["id"] for s in tables["charging_sessions"] if datetime.fromisoformat(s["created_at"]) < datetime.fromisoformat(s["started_at"])],
              "holiday_rows": len(tables["holidays"])}
result = {"at": db["at"], "api_db_comparisons": comparisons, "api_db_mismatches": mismatches, "report_checks": reports,
          "traceability": trace, "chronology": chronology, "reservation_status_counts": dict(Counter(r["status"] for r in tables["reservations"]))}
(OUT / "reconciliation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert not mismatches, "Divergência API/banco: consultar reconciliation.json"
assert all(not r["differences"] and r["invoices_count_matches"] for r in reports)
print(json.dumps({"api_db_checks": len(comparisons), "mismatches": len(mismatches), "reports": reports, "chronology": chronology}, ensure_ascii=False))
