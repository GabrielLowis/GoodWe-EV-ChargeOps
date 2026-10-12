"""Demonstração ponta a ponta da Frente 3 (banco + motor de rateio).

Uso, a partir da raiz do repositório (PostgreSQL rodando, ver README_FRENTE3.md):

    python scripts/demo_frente3.py --reset

--reset recria o schema do banco apontado por DATABASE_URL (apaga os dados!).
A saída deste script está salva em evidencias/frente3/demo_output.txt.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from backend import config  # noqa: E402
from backend.db.base import make_engine, make_session_factory  # noqa: E402
from backend.db.enums import AnomalyStatus  # noqa: E402
from backend.db.models import Anomaly, AuditEvent, ChargingSession, Invoice  # noqa: E402
from backend.faturamento import (  # noqa: E402
    close_invoice,
    generate_invoices_for_period,
    revenue_report,
    review_anomaly,
)
from backend.rateio.money import brl, pt_number  # noqa: E402
from backend.seeds.demo import seed_demo  # noqa: E402

SEPTEMBER = date(2026, 9, 1)
EVIDENCE_DIR = ROOT / "evidencias" / "frente3"


def title(text_: str) -> None:
    print(f"\n{'=' * 90}\n{text_}\n{'=' * 90}")


def money(value: object) -> str:
    return brl(Decimal(str(value)))


def reset_schema() -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", config.DATABASE_URL)
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="recria o schema (apaga os dados do banco)")
    args = parser.parse_args()

    title("EV ChargeOps - Frente 3: banco de dados e motor de rateio (demonstração)")
    print(f"Banco: {config.DATABASE_URL.split('@')[-1]} | fuso: {config.CONDO_TIMEZONE.key}")
    if args.reset:
        reset_schema()
        print("Schema recriado do zero pela migration 0001 (alembic downgrade base + upgrade head).")

    engine = make_engine()
    Session = make_session_factory(engine)
    with Session() as db:
        # 1. Cenário 
        ids = seed_demo(db)
        db.commit()
        title("1. Cenário de setembro/2026 carregado (dados fictícios)")
        sessions = db.scalars(select(ChargingSession).order_by(ChargingSession.started_at)).all()
        names = {v: k for k, v in ids.sessions.items()}
        print(f"{'':4}{'início':<17}{'morador':<10}{'kWh':>8}{'Green':>8}{'Grid':>8}  {'encerramento':<15}validação")
        for s in sessions:
            who = s.user.name.split()[0] if s.user else "(nenhum)"
            print(
                f"{names[s.id]:<4}{s.started_at.astimezone(config.CONDO_TIMEZONE):%d/%m %H:%M}      {who:<10}"
                f"{pt_number(s.total_kwh, 3):>8}{pt_number(s.green_kwh, 3):>8}{pt_number(s.grid_kwh, 3):>8}  "
                f"{s.end_status:<15}{s.validation_status}"
            )

        # 2. Fila de anomalias e revisão 
        title("2. Fila de anomalias do síndico (sessões suspensas antes da fatura)")
        for anomaly in db.scalars(select(Anomaly).order_by(Anomaly.id)).all():
            print(
                f"Anomalia {anomaly.id} | sessão {names[anomaly.session_id]} | detector={anomaly.detector} "
                f"| score={anomaly.score} | {'; '.join(anomaly.reasons)}"
            )
        review_anomaly(
            db,
            ids.anomalies["S0"],
            AnomalyStatus.APPROVED,
            ids.users["manager"],
            "Morador comprovou recarga completa após viagem; energia coerente com 7 kW.",
        )
        review_anomaly(
            db,
            ids.anomalies["S6"],
            AnomalyStatus.REJECTED,
            ids.users["manager"],
            "Medição impossível para o carregador de 7 kW; registro corrompido, não cobrar.",
        )
        db.commit()
        print("\nSíndica aprovou S0 e rejeitou S6. Eventos gravados pelo gatilho de auditoria:")
        for event in db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "anomaly").order_by(AuditEvent.id)):
            print(
                f"  audit #{event.id} {event.action:<17} anomalia={event.entity_id} ator={event.actor_user_id} "
                f"antes={event.before_data} depois={event.after_data and event.after_data.get('status')}"
            )

        # 3. Faturas 
        title("3. Faturas de setembro/2026 (uma por morador, inclusive fatura zero)")
        invoices = generate_invoices_for_period(db, SEPTEMBER, actor_user_id=ids.users["manager"])
        db.commit()
        header = f"{'morador':<14}{'unid.':<7}{'sess.':>5}{'Green':>11}{'Grid':>11}{'Ocios.':>9}"
        print(header + f"{'Subtotal':>11}{'Imposto':>10}{'Overhead':>10}{'TOTAL':>11}")
        for inv in invoices:
            print(
                f"{inv.user.name:<14}{inv.calculation['user']['unit'] or '-':<7}{inv.sessions_count:>5}"
                f"{money(inv.green_amount):>11}{money(inv.grid_amount):>11}{money(inv.idle_amount):>9}"
                f"{money(inv.subtotal):>11}{money(inv.tax_amount):>10}{money(inv.overhead_amount):>10}"
                f"{money(inv.total):>11}"
            )
            for note in inv.calculation["notes"]:
                print(f"{'':14}nota: {note}")
            for skipped in inv.calculation["not_included"]:
                print(f"{'':14}não incluída: sessão {names[skipped['session_id']]} - {skipped['reason']}")

        # 4. Memória de cálculo 
        by_user = {inv.user_id: inv for inv in invoices}
        for person in ("ana", "diego"):
            inv = by_user[ids.users[person]]
            title(f"4. Memória de cálculo - fatura de {inv.user.name} ({inv.calculation['period']})")
            for item in inv.items:
                calc = item.calculation
                late = " | LANÇAMENTO POSTERIOR" if item.is_late_entry else ""
                print(
                    f"\nSessão {names[item.session_id]} | regra: {item.charge_rule} | tarifa: {calc['tariff']['name']}"
                    f" | divisão: {calc['band_split']['method']} | fim da energia: "
                    f"{calc['session']['energy_end_source']}{late}"
                )
                for line in calc["explanation"]:
                    print(f"   {line}")
            print(f"\nTOTAL DA FATURA: {money(inv.total)}")

        # 5. Fechamento e imutabilidade 
        title("5. Fechamento: fatura fechada não muda silenciosamente")
        for inv in invoices:
            close_invoice(db, inv.id, ids.users["manager"])
        db.commit()
        print(f"{len(invoices)} faturas fechadas.")
        ana_invoice = by_user[ids.users["ana"]]
        try:
            db.execute(
                text(
                    "UPDATE invoices SET total = 0, subtotal = 0, green_amount = 0, grid_amount = 0, "
                    "idle_amount = 0, tax_amount = 0, overhead_amount = 0 WHERE id = :id"
                ),
                {"id": ana_invoice.id},
            )
            db.commit()
            print("ATENÇÃO: o banco aceitou a alteração (não deveria)!")
        except IntegrityError as error:
            db.rollback()
            print(f"Tentativa de zerar a fatura da Ana foi RECUSADA pelo banco:\n   {error.orig.diag.message_primary}")

        # 6. Relatório de arrecadação 
        title("6. Relatório de arrecadação para o síndico (fechamento com o condomínio)")
        report = revenue_report(db, SEPTEMBER)
        totals, reimb, balance = report["totals"], report["condominium_reimbursement"], report["energy_balance"]
        print(
            f"Faturas: {totals['invoices_count']} ({totals['closed_invoices']} fechadas) | total arrecadado: "
            f"{money(totals['total'])}"
        )
        print(f"  Reembolso de energia ao condomínio (Green + Grid): {money(reimb['energy_amount'])}")
        print(
            f"  Ociosidade: {money(reimb['idle_amount'])} | Overhead: {money(reimb['overhead_amount'])} | "
            f"Imposto destacado a recolher: {money(reimb['tax_to_collect'])}"
        )
        delivered = pt_number(Decimal(balance["delivered_kwh"]), 3)
        print(f"\nBalanço de energia das sessões iniciadas em setembro: {delivered} kWh entregues")
        labels = {
            "billed": "faturada",
            "system_failure_not_charged": "falha do sistema (não cobrada)",
            "waiting_review": "aguardando revisão",
            "rejected": "rejeitada na revisão",
            "unattributed": "sem morador atribuído",
            "approved_not_invoiced": "aprovada e ainda não faturada",
        }
        for key, label in labels.items():
            bucket = balance[key]
            sessions_txt = ", ".join(names[i] for i in bucket["session_ids"]) or "-"
            kwh_txt = pt_number(Decimal(bucket["kwh"]), 3)
            print(f"  {label:<34}{bucket['count']:>3} sessão(ões) {kwh_txt:>9} kWh   [{sessions_txt}]")
        late = balance["late_entries_from_previous_periods"]
        print(
            f"  + lançamentos posteriores de meses anteriores: {late['count']} "
            f"({pt_number(Decimal(late['kwh']), 3)} kWh, "
            f"{money(late['amount'])})"
        )

        # 7. Arquivos de evidência 
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        ana = db.get(Invoice, ana_invoice.id)
        export = {
            "invoice": {c: str(getattr(ana, c)) for c in ("id", "user_id", "period", "status", "total")},
            "calculation": ana.calculation,
            "items": [
                {"session_id": i.session_id, "total": str(i.total), "calculation": i.calculation} for i in ana.items
            ],
        }
        (EVIDENCE_DIR / "fatura_ana_2026-09.json").write_text(json.dumps(export, indent=2, ensure_ascii=False))
        (EVIDENCE_DIR / "relatorio_arrecadacao_2026-09.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False)
        )
        title("Fim. JSONs salvos em evidencias/frente3/ (fatura da Ana e relatório de arrecadação).")


if __name__ == "__main__":
    main()
