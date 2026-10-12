"""Período de faturamento = mês civil no fuso do condomínio."""

from __future__ import annotations
# date = só o dia; datetime = dia e hora (com fuso); time = só a hora.
from datetime import date, datetime, time

# ZoneInfo representa um fuso horário, como ZoneInfo("America/Sao_Paulo").
from zoneinfo import ZoneInfo

# Qualquer dia do mês - primeiro dia do mesmo mês.
def first_day(period: date) -> date:
    return period.replace(day=1)

# Primeiro dia do mês seguinte.
def next_month(period: date) -> date:
    period = first_day(period)
    return date(period.year + (period.month // 12), period.month % 12 + 1, 1)

# Limites do mês no horário do condomínio
def month_bounds(period: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Início (inclusive) e fim (exclusive) do mês, à meia-noite local."""
    start = datetime.combine(first_day(period), time(0), tzinfo=tz)
    end = datetime.combine(next_month(period), time(0), tzinfo=tz)
    return start, end

# Nome do período para relatórios e JSONs, no formato 2026-09.
def period_label(period: date) -> str:
    return f"{period.year:04d}-{period.month:02d}"
