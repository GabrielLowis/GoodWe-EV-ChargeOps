"""Recomendacao de janela de recarga (baseline deterministico).

Estima, para cada hora das proximas 24h, a fracao de energia solar disponivel
(curva simples, pico ao meio-dia) e calcula o custo de energia. Serve como
baseline ate o modelo de regressao ser treinado e integrado.
"""
import datetime
import math
from decimal import Decimal

from services.rateio import Band, band_at


def solar_fraction(hour: int) -> float:
    """Fracao estimada de energia verde na hora do dia (0 a 1). Hipotese simples: seno entre 6h e 18h."""
    if hour < 6 or hour >= 18:
        return 0.0
    return max(0.0, math.sin(math.pi * (hour - 6) / 12))


def estimate_cost(start: datetime.datetime, kwh: float, power_kw: float, bands: list[Band]) -> Decimal:
    hours = max(1, math.ceil(kwh / power_kw))
    kwh_per_hour = Decimal(str(kwh)) / Decimal(hours)
    total = Decimal("0")
    for i in range(hours):
        t = start + datetime.timedelta(hours=i)
        band = band_at(bands, t.time())
        if band is None:
            raise ValueError("Sem faixa tarifaria cobrindo o horario")
        g = Decimal(str(round(solar_fraction(t.hour), 4)))
        price = g * band.green_price + (Decimal("1") - g) * band.grid_price
        total += kwh_per_hour * price
    return total.quantize(Decimal("0.01"))


def recommend_window(now: datetime.datetime, kwh: float, power_kw: float, bands: list[Band], horizon_h: int = 24) -> dict:
    start0 = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    options = []
    for h in range(horizon_h):
        start = start0 + datetime.timedelta(hours=h)
        options.append((estimate_cost(start, kwh, power_kw, bands), start))
    best_cost, best_start = min(options, key=lambda o: (o[0], o[1]))
    now_cost = estimate_cost(now, kwh, power_kw, bands)
    return {
        "recommended_start": best_start,
        "predicted_cost": best_cost,
        "cost_if_now": now_cost,
        "savings": max(Decimal("0"), now_cost - best_cost),
        "model": "baseline-deterministico",
    }
