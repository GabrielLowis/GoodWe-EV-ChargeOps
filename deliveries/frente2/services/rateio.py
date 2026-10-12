"""Motor de rateio: funcoes puras (sem banco), faceis de testar e de explicar.

Formula:  Green + Grid + Ociosidade = Subtotal;  Imposto e Overhead incidem sobre o Subtotal.
"""
import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
FINE = Decimal("0.0001")


def to_cents(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def to_fine(v: Decimal) -> Decimal:
    return v.quantize(FINE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Band:
    name: str
    start: datetime.time
    end: datetime.time
    green_price: Decimal
    grid_price: Decimal

    def contains(self, t: datetime.time) -> bool:
        if self.start == self.end:          # faixa de 24h
            return True
        if self.start < self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end   # faixa que atravessa a meia-noite


@dataclass(frozen=True)
class Config:
    idle_fee_per_min: Decimal
    idle_tolerance_min: int
    tax_pct: Decimal
    overhead_pct: Decimal


def band_at(bands: list[Band], t: datetime.time) -> Band | None:
    for b in bands:
        if b.contains(t):
            return b
    return None


def split_segments(start: datetime.datetime, end: datetime.datetime, bands: list[Band]):
    """Parte a sessao em trechos, um por faixa tarifaria atravessada."""
    cuts = {start, end}
    day = start.date()
    while day <= end.date():
        for b in bands:
            for edge in (b.start, b.end):
                point = datetime.datetime.combine(day, edge)
                if start < point < end:
                    cuts.add(point)
        day += datetime.timedelta(days=1)
    points = sorted(cuts)
    segments = []
    for a, b in zip(points, points[1:]):
        band = band_at(bands, a.time())
        if band is None:
            raise ValueError(f"Nenhuma faixa tarifaria cobre o horario {a.time()}")
        segments.append((a, b, band))
    return segments


def estimate_idle_minutes(total_kwh: float, max_power_kw: float, start: datetime.datetime, end: datetime.datetime) -> int:
    """Estimativa de minutos ocupando o carregador sem receber energia.

    Hipotese (validar com a Pessoa 1): a SEMS nao informa o fim do fluxo de energia, entao
    estimamos o tempo de carga como total_kwh / max_power_kw e o resto da sessao como ocioso.
    """
    if max_power_kw <= 0:
        return 0
    duration_min = (end - start).total_seconds() / 60
    charge_min = total_kwh / max_power_kw * 60
    return max(0, int(duration_min - charge_min))


def billable_idle_minutes(idle_minutes: int, tolerance_min: int, failed: bool) -> int:
    """So cobra o que passa da tolerancia. Falha do sistema nunca gera cobranca."""
    if failed:
        return 0
    return max(0, idle_minutes - tolerance_min)


def calculate_charge(*, started_at, ended_at, total_kwh, green_kwh, grid_kwh, max_power_kw,
                     failed: bool, bands: list[Band], config: Config) -> dict:
    total_seconds = Decimal(str((ended_at - started_at).total_seconds()))
    if total_seconds <= 0:
        raise ValueError("A sessao precisa ter duracao positiva")

    green = Decimal(str(green_kwh))
    grid = Decimal(str(grid_kwh))

    # Energia particionada por faixa: cada trecho recebe uma fracao proporcional ao tempo
    # (hipotese: potencia constante, pois nao ha curva minuto a minuto).
    segments_memory = []
    green_sum = Decimal("0")
    grid_sum = Decimal("0")
    for seg_start, seg_end, band in split_segments(started_at, ended_at, bands):
        fraction = Decimal(str((seg_end - seg_start).total_seconds())) / total_seconds
        seg_green = green * fraction
        seg_grid = grid * fraction
        green_cost = to_fine(seg_green * band.green_price)
        grid_cost = to_fine(seg_grid * band.grid_price)
        green_sum += green_cost
        grid_sum += grid_cost
        segments_memory.append({
            "band": band.name,
            "from": seg_start.isoformat(),
            "to": seg_end.isoformat(),
            "fraction": str(to_fine(fraction)),
            "green_kwh": str(seg_green.quantize(Decimal("0.0001"))),
            "grid_kwh": str(seg_grid.quantize(Decimal("0.0001"))),
            "green_price": str(band.green_price),
            "grid_price": str(band.grid_price),
            "green_cost": str(green_cost),
            "grid_cost": str(grid_cost),
        })

    idle_total = estimate_idle_minutes(total_kwh, max_power_kw, started_at, ended_at)
    idle_billable = billable_idle_minutes(idle_total, config.idle_tolerance_min, failed)

    green_cost_c = to_cents(green_sum)
    grid_cost_c = to_cents(grid_sum)
    idle_cost_c = to_cents(Decimal(idle_billable) * config.idle_fee_per_min)
    subtotal = green_cost_c + grid_cost_c + idle_cost_c
    tax = to_cents(subtotal * config.tax_pct / Decimal("100"))
    overhead = to_cents(subtotal * config.overhead_pct / Decimal("100"))
    total = subtotal + tax + overhead

    memory = {
        "formula": "subtotal = green + grid + ociosidade; total = subtotal + imposto + overhead",
        "assumptions": [
            "Energia distribuida entre as faixas proporcionalmente ao tempo (potencia constante).",
            "Ociosidade estimada: duracao - total_kwh/max_power_kw.",
        ],
        "config": {
            "idle_fee_per_min": str(config.idle_fee_per_min),
            "idle_tolerance_min": config.idle_tolerance_min,
            "tax_pct": str(config.tax_pct),
            "overhead_pct": str(config.overhead_pct),
        },
        "session_failed": failed,
        "segments": segments_memory,
        "idle": {"estimated_minutes": idle_total, "billable_minutes": idle_billable, "cost": str(idle_cost_c)},
        "components": {
            "green": str(green_cost_c), "grid": str(grid_cost_c), "idle": str(idle_cost_c),
            "subtotal": str(subtotal), "tax": str(tax), "overhead": str(overhead), "total": str(total),
        },
    }
    return {
        "green_cost": green_cost_c, "grid_cost": grid_cost_c, "idle_cost": idle_cost_c,
        "subtotal": subtotal, "tax": tax, "overhead": overhead, "total": total, "memory": memory,
    }
