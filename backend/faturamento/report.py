"""Relatório mensal de arrecadação para o síndico (fechamento com o condomínio).

Responde a três perguntas do fechamento:
  1. Quanto cada morador pagou e quanto disso é energia (reembolso ao condomínio)?
  2. Quanto é imposto destacado, overhead e ociosidade?
  3. Toda a energia entregue pelos carregadores foi faturada? Se não, por quê?
"""

from __future__ import annotations

# Iterable: "qualquer coisa que dá para percorrer com for" (lista, tupla, gerador...). Aqui é usado só como tipo.
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend import config
from backend.db.enums import SessionEndStatus, ValidationStatus
from backend.db.models import ChargingSession, Invoice, InvoiceItem, User
from backend.faturamento.periods import first_day, month_bounds, period_label

# ZERO: o número 0 como Decimal. dec_str: Decimal -> texto com casas fixas (ex.: "43.54").
from backend.rateio.money import ZERO, dec_str

# Nomes das colunas de dinheiro da fatura. Com esta lista, o código percorre os 7 campos com um "for"
# em vez de repetir 7 linhas parecidas.
_MONEY_FIELDS = ("green_amount", "grid_amount", "idle_amount", "subtotal", "tax_amount", "overhead_amount", "total")


def revenue_report(db: Session, period: date, tz: ZoneInfo = config.CONDO_TIMEZONE) -> dict[str, Any]:
    # Qualquer dia do mês vira o dia 1; start e end são 01/mês 00:00 e 01/mês seguinte 00:00.
    period = first_day(period)
    start, end = month_bounds(period, tz)

    # Faturas do mês, já com o morador, a unidade dele e os itens (evita uma consulta por fatura).
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.period == period)
            .options(selectinload(Invoice.user).selectinload(User.unit), selectinload(Invoice.items))
            .order_by(Invoice.user_id)
        )
    )

    # Uma linha por fatura, com os valores já formatados como texto.
    rows = []
    for inv in invoices:
        rows.append(
            {
                "invoice_id": inv.id,
                "user_id": inv.user_id,
                "user_name": inv.user.name,
                "unit": inv.user.unit.label if inv.user.unit else None,  # ex.: "A-101"; None se não tiver unidade
                "status": inv.status,
                "sessions_count": inv.sessions_count,
                "green_kwh": dec_str(inv.green_kwh, 3),
                "grid_kwh": dec_str(inv.grid_kwh, 3),
                # Acrescenta os 7 campos de dinheiro de uma vez. getattr(inv, "total") é o mesmo que inv.total,
                # mas com o nome do campo numa variável. O ** "espalha" esse dicionário dentro deste.
                **{f: dec_str(getattr(inv, f), 2) for f in _MONEY_FIELDS},
            }
        )

    # Soma de cada campo de dinheiro em todas as faturas, e a energia total faturada (kWh).
    totals = {f: _sum(getattr(inv, f) for inv in invoices) for f in _MONEY_FIELDS}
    billed_kwh = _sum(inv.green_kwh + inv.grid_kwh for inv in invoices)
    # Itens de lançamento posterior: sessões de meses anteriores que só foram cobradas neste mês.
    late_items = [item for inv in invoices for item in inv.items if item.is_late_entry]

    # Balanço de energia: todas as sessões encerradas que começaram no mês, de qualquer morador.
    sessions = list(
        db.scalars(
            select(ChargingSession).where(
                ChargingSession.started_at >= start,
                ChargingSession.started_at < end,
                ChargingSession.end_status != SessionEndStatus.IN_PROGRESS,
            )
        )
    )
    # Quais dessas sessões aparecem em algum item de fatura. set é um conjunto: perguntar "este id está aqui?" é instantâneo.
    invoiced_ids = set(
        db.scalars(select(InvoiceItem.session_id).where(InvoiceItem.session_id.in_([s.id for s in sessions])))
    )

    # Um "balde" para cada destino possível da energia.
    buckets: dict[str, list[ChargingSession]] = {
        "billed": [],  # faturada
        "system_failure_not_charged": [],  # falha do sistema: registrada, mas nunca cobrada
        "waiting_review": [],  # pendente (aguarda validação) ou suspensa (aguarda o síndico)
        "rejected": [],  # descartada na revisão de anomalia
        "unattributed": [],  # sem morador atribuído
        "approved_not_invoiced": [],  # aprovada, mas ainda não entrou em nenhuma fatura
    }
    # Cada sessão cai em exatamente um balde. A ordem dos testes importa: a falha vem primeiro porque
    # aparece na fatura com valor zero e, mesmo assim, não foi cobrada.
    for s in sessions:
        if s.end_status == SessionEndStatus.SYSTEM_FAILURE:
            buckets["system_failure_not_charged"].append(s)
        elif s.id in invoiced_ids:
            buckets["billed"].append(s)
        elif s.user_id is None:
            buckets["unattributed"].append(s)
        elif s.validation_status == ValidationStatus.REJECTED:
            buckets["rejected"].append(s)
        elif s.validation_status in (ValidationStatus.PENDING, ValidationStatus.SUSPENDED):
            buckets["waiting_review"].append(s)
        else:
            buckets["approved_not_invoiced"].append(s)

    # Resultado. A energia cobrada (Green + Grid) é o que reembolsa a conta de luz paga pelo condomínio.
    energy_amount = totals["green_amount"] + totals["grid_amount"]
    return {
        "period": period_label(period),
        "invoices": rows,
        "totals": {
            **{f: dec_str(v, 2) for f, v in totals.items()},
            "invoices_count": len(invoices),
            # sum(1 for ...) conta quantas faturas já estão fechadas.
            "closed_invoices": sum(1 for inv in invoices if inv.status == "closed"),
            "billed_kwh": dec_str(billed_kwh, 3),
        },
        # O que volta para o condomínio e o que precisa ser recolhido ao governo.
        "condominium_reimbursement": {
            "energy_amount": dec_str(energy_amount, 2),
            "idle_amount": dec_str(totals["idle_amount"], 2),
            "overhead_amount": dec_str(totals["overhead_amount"], 2),
            "tax_to_collect": dec_str(totals["tax_amount"], 2),
            "description": (
                "Energia (Green + Grid) reembolsa o que o condomínio pagou à distribuidora; ociosidade e "
                "overhead ficam com o condomínio; o imposto destacado deve ser recolhido."
            ),
        },
        "energy_balance": {
            "delivered_kwh": dec_str(_sum(s.total_kwh for s in sessions), 3),
            "sessions_in_period": len(sessions),
            # Um resumo (quantidade, kWh e ids) para cada balde.
            **{name: _bucket(items) for name, items in buckets.items()},
            "late_entries_from_previous_periods": {
                "count": len(late_items),
                "kwh": dec_str(_sum(i.green_kwh + i.grid_kwh for i in late_items), 3),
                "amount": dec_str(_sum(i.total for i in late_items), 2),
            },
        },
    }


# Soma que começa em ZERO (Decimal). O sum() comum começa no inteiro 0: com uma lista vazia, devolveria 0
# (int), e o dec_str não sabe formatar int. Começando em ZERO, o resultado é sempre Decimal.
def _sum(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)


# Resumo de um balde: quantas sessões, quantos kWh e quais ids (para o síndico conferir uma a uma).
def _bucket(sessions: list[ChargingSession]) -> dict[str, Any]:
    return {
        "count": len(sessions),
        "kwh": dec_str(_sum(s.total_kwh for s in sessions), 3),
        "session_ids": [s.id for s in sessions],
    }

