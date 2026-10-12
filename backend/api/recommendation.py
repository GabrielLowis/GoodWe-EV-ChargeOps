"""Baseline demonstrativo: preços reais do cadastro, geração solar hipotética explícita."""
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from math import sin, pi
from fastapi import HTTPException
from sqlalchemy import select
from backend import config
from backend.db.models import Charger, Reservation
from backend.faturamento import repository as repo
from backend.faturamento.mappers import tariff_to_spec, tax_rule_to_spec
from backend.rateio.engine import calculate_session
from backend.rateio.models import SessionInput
from backend.api.schemas import RecommendationOut


def recommend(db, charger: Charger, kwh: Decimal, power: Decimal, now: datetime | None = None):
    if power > charger.rated_power_kw:
        raise HTTPException(422, "Potência solicitada acima da capacidade cadastrada")
    duration = timedelta(seconds=float(kwh / power * 3600))
    if duration > timedelta(hours=12):
        raise HTTPException(422, "Estimativa ultrapassa o limite de 12 horas da reserva")
    now = now or datetime.now(UTC)
    holidays = repo.all_holidays(db)

    def estimate(start):
        tariff = repo.tariff_at(db, start)
        if tariff is None:
            return None
        # Aproximação por amostras horárias, independente do modelo de anomalias.
        steps = max(1, int(duration.total_seconds() / 3600) + 1)
        solar = sum(max(0.0, sin(pi * (((start + duration * ((i + .5) / steps))
                                     .astimezone(config.CONDO_TIMEZONE).hour) - 6) / 12))
                    for i in range(steps)) / steps
        green = (kwh * Decimal(str(solar))).quantize(Decimal("0.001"))
        input_ = SessionInput(session_id="forecast", user_id=1, started_at=start, ended_at=start + duration,
                              energy_ended_at=start + duration, total_kwh=kwh, green_kwh=green,
                              grid_kwh=kwh-green, end_status="completed", validation_status="approved",
                              charger_rated_power_kw=charger.rated_power_kw)
        taxes = [tax_rule_to_spec(r) for r in repo.tax_rules_at(db, start, config.TAX_JURISDICTION)]
        return calculate_session(input_, tariff_to_spec(tariff), taxes, holidays, config.CONDO_TIMEZONE).total

    immediate = estimate(now)
    if immediate is None:
        raise HTTPException(422, "Não há tarifa vigente para estimar o custo atual")
    first = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    candidates = []
    for i in range(24):
        start = first + timedelta(hours=i)
        occupied = set(db.scalars(select(Reservation.connector).where(
            Reservation.charger_id == charger.id, Reservation.status.in_(["active", "in_use"]),
            Reservation.starts_at < start + duration, Reservation.ends_at > start)))
        if len(occupied) >= charger.connectors:
            continue
        cost = estimate(start)
        if cost is not None:
            candidates.append((cost, start))
    if not candidates:
        raise HTTPException(409, "Nenhuma janela disponível no horizonte de 24 horas")
    cost, start = min(candidates)
    return RecommendationOut(recommended_start=start, recommended_end=start+duration, predicted_cost=cost,
                             cost_if_now=immediate, savings=max(Decimal("0.00"), immediate-cost),
                             model="baseline-deterministico", assumptions=[
                                 "Geração solar hipotética por hora; não usa previsão meteorológica nem regressão.",
                                 "Tarifas e impostos cadastrados; potência constante; sem ociosidade prevista.",
                                 "Disponibilidade consultada agora; somente criar a reserva garante a janela."])
