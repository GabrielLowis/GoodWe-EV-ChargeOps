"""Camadas 1 e 2 da deteccao de anomalias (estrutural e fisica)."""
import os


def _reason(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def charger_max_kw() -> float:
    return float(os.getenv("CHARGER_MAX_KW", "22"))


def layer1_structural(s) -> list[dict]:
    """Campos coerentes entre si: tempo, sinais e soma das origens de energia."""
    reasons = []
    if s.ended_at <= s.started_at:
        reasons.append(_reason("TIME_INCONSISTENT", "ended_at deve ser maior que started_at"))
    if min(s.total_kwh, s.green_kwh, s.grid_kwh, s.average_power_kw, s.max_power_kw) < 0:
        reasons.append(_reason("NEGATIVE_VALUE", "Energia e potencia nao podem ser negativas"))
    tolerance = max(0.05, 0.01 * abs(s.total_kwh))
    if abs((s.green_kwh + s.grid_kwh) - s.total_kwh) > tolerance:
        reasons.append(_reason(
            "ENERGY_MISMATCH",
            f"green_kwh + grid_kwh = {s.green_kwh + s.grid_kwh:.2f} difere de total_kwh = {s.total_kwh:.2f}"))
    if s.max_power_kw < s.average_power_kw:
        reasons.append(_reason("POWER_INCONSISTENT", "max_power_kw menor que average_power_kw"))
    return reasons


def layer2_physical(s) -> list[dict]:
    """Fisicamente possivel? Energia = potencia x tempo."""
    reasons = []
    limit = charger_max_kw()
    if s.max_power_kw > limit * 1.05:
        reasons.append(_reason(
            "EXCEEDS_CHARGER_POWER",
            f"max_power_kw = {s.max_power_kw:.1f} excede o limite do carregador ({limit:.0f} kW)"))
    hours = (s.ended_at - s.started_at).total_seconds() / 3600
    deliverable = s.max_power_kw * hours
    if s.total_kwh > deliverable * 1.05 + 0.05:
        reasons.append(_reason(
            "PHYSICAL_IMPOSSIBLE",
            f"{s.total_kwh:.1f} kWh em {hours * 60:.0f} min excede {s.max_power_kw:.1f} kW de potencia maxima"))
    return reasons
