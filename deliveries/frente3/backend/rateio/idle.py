"""Tarifa de ociosidade (overstay).

Regra da Sprint 1: cobram-se os minutos em que o veículo continua ocupando a
vaga depois do fim do fluxo de energia, descontada a tolerância de 15 minutos,
multiplicados pela taxa por minuto definida pela assembleia.

Critérios de aceite do plano da Sprint 2:
    14 min -> R$ 0 | 15 min -> R$ 0 | 16 min -> 1 min cobrado | falha do sistema -> R$ 0

Contam-se apenas minutos completos (15 min 59 s = 15 min): na dúvida, a
favor do morador.
"""

# Comparação que ajuda: é como o estacionamento do shopping. Os primeiros 15 minutos depois do fim da carga são grátis; a partir daí, cada minuto completo com o carro parado na vaga é cobrado.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.rateio.allocation import derive_energy_end
from backend.rateio.models import SessionInput
from backend.rateio.money import seconds_between

# De onde veio o horário do fim da energia (fica registrado na memória de cálculo).
# A fonte de dados informou.
SOURCE_INFORMED = "informed"
# O motor descobriu pela curva de potência.
SOURCE_POWER_CURVE = "power_curve"
# Ninguém sabe: nesse caso, nada de ociosidade
SOURCE_UNKNOWN = "unknown"

ENERGY_END_SOURCE_LABELS = {
    SOURCE_INFORMED: "informado pela fonte de dados (SEMS/gateway)",
    SOURCE_POWER_CURVE: "estimado pela curva de potência (primeira leitura sem fluxo)",
    SOURCE_UNKNOWN: "desconhecido: sem dado para provar ociosidade, nada é cobrado",
}

# O resultado do cálculo de ociosidade de uma sessão.
@dataclass(frozen=True)
class IdleResult:
    # Quando a energia parou (None = desconhecido).
    energy_end: datetime | None
    # De onde veio esse horário (constantes acima).
    energy_end_source: str
    # Minutos completos entre o fim da energia e a desconexão.
    minutes_after_energy_end: int
    # Tolerância da tarifa (15).
    tolerance_minutes: int
    # Minutos cobrados = os de cima menos a tolerância.
    billable_minutes: int

# Minutos cobráveis. max(0, ...) impede número negativo.
def billable_idle_minutes(minutes_after_energy_end: int, tolerance_minutes: int) -> int:
    """Minutos cobráveis = minutos completos após o fim da energia - tolerância (nunca negativo)."""
    return max(0, minutes_after_energy_end - tolerance_minutes)

# Descobre quando a energia parou, nesta ordem: 1) informado pela fonte; 2) estimado pela curva; 3) desconhecido.
def resolve_energy_end(session: SessionInput) -> tuple[datetime | None, str]:
    """Fim do fluxo de energia: informado pela fonte, estimado pela curva ou desconhecido."""
    if session.energy_ended_at is not None:
        return session.energy_ended_at, SOURCE_INFORMED
    derived = derive_energy_end(session.power_samples, session.ended_at)
    if derived is not None:
        return derived, SOURCE_POWER_CURVE
    return None, SOURCE_UNKNOWN


def compute_idle(session: SessionInput, tolerance_minutes: int) -> IdleResult:
    energy_end, source = resolve_energy_end(session)
    # Sem saber quando a energia parou (ou quando o carro saiu), não dá para provar ociosidade: zero.
    if energy_end is None or session.ended_at is None:
        return IdleResult(None, SOURCE_UNKNOWN, 0, tolerance_minutes, 0)

    # O fim do fluxo precisa estar dentro da sessão.
    energy_end = max(session.started_at, min(energy_end, session.ended_at))
    whole_minutes = int(seconds_between(energy_end, session.ended_at) // 60)
    return IdleResult(
        energy_end=energy_end,
        energy_end_source=source,
        minutes_after_energy_end=whole_minutes,
        tolerance_minutes=tolerance_minutes,
        billable_minutes=billable_idle_minutes(whole_minutes, tolerance_minutes),
    )
