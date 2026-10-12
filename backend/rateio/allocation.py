"""Distribuição da energia medida entre os trechos de faixa.

O medidor (campos Green/Grid da SEMS) informa quanto foi entregue na sessão
inteira, mas não em cada faixa. Estimamos a fração de cada trecho assim:

1. Curva de potência (preferencial): integra a potência (kW) no tempo dentro
   de cada trecho (regra do trapézio). A curva define só a PROPORÇÃO; o total
   cobrado continua sendo o kWh do medidor.
2. Proporcional ao tempo (reserva): sem curva confiável, assume potência
   constante. A memória de cálculo registra qual método foi usado.

No fim, os kWh de cada trecho são arredondados a 1 Wh pelo método dos maiores
restos, para que a soma dos trechos feche exatamente com o total medido.
"""

from __future__ import annotations

# Sequence: "qualquer lista ou tupla" (usado só como tipo).
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

# pairwise percorre uma lista de dois em dois vizinhos: [a, b, c] -> (a, b), (b, c).
from itertools import pairwise

from backend.rateio.models import PowerSample, Segment
from backend.rateio.money import KWH_QUANTUM, ZERO, seconds_between

# Nomes dos dois métodos, gravados na memória de cálculo.
METHOD_POWER_CURVE = "power_curve"
METHOD_TIME = "time_proportional"

METHOD_DESCRIPTIONS = {
    METHOD_POWER_CURVE: "Proporção de cada trecho calculada pela curva de potência (integração da potência no tempo).",
    METHOD_TIME: "Sem curva de potência suficiente: proporção de cada trecho estimada pelo tempo (potência constante).",
}

# A curva só é usada se cobrir pelo menos 90% do intervalo de carga.
MIN_CURVE_COVERAGE = Decimal("0.9")

# Abaixo desta potência consideramos que não há fluxo de energia.
FLOW_THRESHOLD_KW = Decimal("0.1")

_HOUR = Decimal(3600)

# Método dos maiores restos, com o exemplo do guia de estudo: dividir 7,500 kWh em pesos 30 e 40.
#   - Em unidades de 1 Wh, são 7500 unidades. As cotas exatas são 3214,28... e 4285,71...
#   - Os pisos (parte inteira) somam 3214 + 4285 = 7499: sobrou 1 unidade.
#   - A sobra vai para a maior fração (0,71): 3,214 + 4,286 = 7,500 kWh, soma exata.
def split_quantity(total: Decimal, weights: Sequence[Decimal], quantum: Decimal = KWH_QUANTUM) -> list[Decimal]:
    if not weights:
        return []
    weight_sum = sum(weights, ZERO)
    # Quantas unidades de 1 Wh existem no total (to_integral_value arredonda para número inteiro).
    units_total = int((total / quantum).to_integral_value())
    if weight_sum <= 0:
        # sem informação de proporção: tudo no primeiro trecho
        return [total] + [ZERO] * (len(weights) - 1)

    exact_units = [units_total * w / weight_sum for w in weights]
    floors = [int(u) for u in exact_units]  # u >= 0, então int() é o piso
    leftover = units_total - sum(floors)
    # maiores restos primeiro; empate resolvido pelo trecho mais antigo
    ranking = sorted(range(len(weights)), key=lambda i: (-(exact_units[i] - floors[i]), i))
    for index in ranking[:leftover]:
        floors[index] += 1
    return [units * quantum for units in floors]

# Método de reserva: o peso de cada trecho é a sua duração em segundos (potência constante).
def time_weights(segments: Sequence[Segment]) -> list[Decimal]:
    return [seconds_between(s.start, s.end) for s in segments]

# Interpolação linear: estima a potência num momento entre duas medições, "no meio do caminho".
def _power_at(s0: PowerSample, s1: PowerSample, moment: datetime, attr: str) -> Decimal:
    p0 = _value(s0, attr)
    p1 = _value(s1, attr)
    span = seconds_between(s0.measured_at, s1.measured_at)
    if span == 0:
        return p0
    return p0 + (p1 - p0) * seconds_between(s0.measured_at, moment) / span

# Qual potência usar de uma medição: a total, só a solar (green) ou só a da rede (grid = total - solar).
def _value(sample: PowerSample, attr: str) -> Decimal:
    if attr == "grid":
        green = sample.green_power_kw or ZERO
        return max(sample.power_kw - green, ZERO)
    if attr == "green":
        return sample.green_power_kw or ZERO
    return sample.power_kw

# Energia = área sob a curva de potência. Entre duas medições vizinhas, a área é um trapézio:
# média das duas potências x tempo. Somando os trapézios dentro do trecho, tem-se a energia do trecho.
def energy_between(samples: Sequence[PowerSample], start: datetime, end: datetime, attr: str = "total") -> Decimal:
    energy = ZERO
    for s0, s1 in pairwise(samples):
        # Recorta o pedaço entre as duas medições para caber dentro de [start, end).
        lo = max(s0.measured_at, start)
        hi = min(s1.measured_at, end)
        if hi <= lo:
            continue
        p_lo = _power_at(s0, s1, lo, attr)
        p_hi = _power_at(s0, s1, hi, attr)
        # (potência média) x segundos / 3600 = kWh
        energy += (p_lo + p_hi) / 2 * seconds_between(lo, hi) / _HOUR
    return energy

# A curva é confiável o bastante para ser usada?
def curve_is_usable(samples: Sequence[PowerSample], start: datetime, end: datetime) -> bool:
    if len(samples) < 2:
        return False
    interval = seconds_between(start, end)
    if interval <= 0:
        return False
    # Pedaço do intervalo de carga que a curva realmente cobre.
    covered_start = max(samples[0].measured_at, start)
    covered_end = min(samples[-1].measured_at, end)
    if covered_end <= covered_start:
        return False
    if seconds_between(covered_start, covered_end) / interval < MIN_CURVE_COVERAGE:
        return False
    return energy_between(samples, start, end) > 0

# Decide o método e devolve três coisas: os pesos da energia Green, os pesos da Grid e o nome do método.
def allocation_weights(
    segments: Sequence[Segment],
    samples: Sequence[PowerSample],
    charging_start: datetime,
    charging_end: datetime,
) -> tuple[list[Decimal], list[Decimal], str]:
    """Pesos de cada trecho para a energia Green e para a Grid, e o método usado."""
    ordered = sorted(samples, key=lambda s: s.measured_at)
    if curve_is_usable(ordered, charging_start, charging_end):
        total_weights = [energy_between(ordered, s.start, s.end) for s in segments]
        if all(sample.green_power_kw is not None for sample in ordered):
            # a curva separa solar e rede instante a instante: usa cada uma
            green = [energy_between(ordered, s.start, s.end, "green") for s in segments]
            grid = [energy_between(ordered, s.start, s.end, "grid") for s in segments]
            return (
                green if sum(green, ZERO) > 0 else total_weights,
                grid if sum(grid, ZERO) > 0 else total_weights,
                METHOD_POWER_CURVE,
            )
        return total_weights, total_weights, METHOD_POWER_CURVE

    # Sem curva confiável: divide pelo tempo.
    weights = time_weights(segments)
    return weights, weights, METHOD_TIME

# Quando a energia parou, olhando a curva: a última medição com fluxo (> 0,1 kW) e a primeira sem fluxo logo depois dela.
def derive_energy_end(samples: Sequence[PowerSample], ended_at: datetime | None) -> datetime | None:
    ordered = sorted(samples, key=lambda s: s.measured_at)
    last_flow_index = None
    
    # Enumerate dá a posição e a medição ao mesmo tempo; guarda a posição da última com fluxo.
    for index, sample in enumerate(ordered):
        if sample.power_kw > FLOW_THRESHOLD_KW:
            last_flow_index = index
    if last_flow_index is None:
        # Nunca houve fluxo: não dá para dizer quando parou
        return None
    if last_flow_index + 1 < len(ordered):
        # A primeira medição sem fluxo
        return ordered[last_flow_index + 1].measured_at
    # A curva acaba ainda com fluxo: considera que a energia foi até a desconexão
    return ended_at
