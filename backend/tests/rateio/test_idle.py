"""Ociosidade: critérios de aceite do plano da Sprint 2 (sem banco).

14 min = R$ 0; 15 min = R$ 0; 16 min = 1 min cobrado; falha do sistema = R$ 0.
"""

# Como ler este arquivo: em quase todos os testes a energia para às 12:00 (ENERGY_END), e o que muda é
# quanto tempo o carro ficou parado depois disso. A tarifa de teste dá 15 minutos de tolerância e cobra
# R$ 0,25 por minuto além dela.

from datetime import timedelta
from decimal import Decimal as D

import pytest

from backend.db.enums import ChargeRule, SessionEndStatus
from backend.rateio.engine import calculate_session
from backend.rateio.models import PowerSample
from backend.tests.helpers import TZ, at, make_session

FEE = D("0.25")  # R$/min da tarifa de demonstração
ENERGY_END = at(21, 12)


# Calcula uma sessão em que o carro ficou minutes_parked minutos (e seconds segundos) parado depois do fim
# da energia. **overrides repassa outros ajustes para make_session, ex.: charge_for(tariff, 50,
# end_status=SessionEndStatus.USER_STOPPED).
def charge_for(tariff, minutes_parked=0, seconds=0, **overrides):
    session = make_session(
        energy_ended_at=ENERGY_END,
        ended_at=ENERGY_END + timedelta(minutes=minutes_parked, seconds=seconds),
        **overrides,
    )
    return calculate_session(session, tariff, [], frozenset(), TZ)


# Os critérios de aceite do plano, um por execução (6 no total). Cada par é (minutos parado, minutos
# cobrados): até 15 minutos não se paga nada; a partir daí, paga-se só o que passou da tolerância
# (16 -> 1, 30 -> 15, 75 -> 60). O valor em reais é minutos cobrados x R$ 0,25.
@pytest.mark.parametrize(
    ("minutes_parked", "billable"),
    [(0, 0), (14, 0), (15, 0), (16, 1), (30, 15), (75, 60)],
)
def test_criterios_de_aceite_da_tolerancia(tariff, minutes_parked, billable):
    charge = charge_for(tariff, minutes_parked)
    assert charge.idle_minutes == billable
    assert charge.idle_amount == (D(billable) * FEE).quantize(D("0.01"))


# Só minutos completos contam: 15 min e 59 s ainda são 15 minutos (nada a pagar), e 16 min e 59 s são 16
# minutos (1 cobrado). Os segundos que sobram nunca viram cobrança.
def test_so_minutos_completos_contam(tariff):
    assert charge_for(tariff, 15, seconds=59).idle_minutes == 0
    assert charge_for(tariff, 16, seconds=59).idle_minutes == 1


# Falha do sistema: mesmo com o carro parado por 2 horas, não se paga ociosidade (nem nada).
def test_falha_do_sistema_nao_paga_ociosidade(tariff):
    charge = charge_for(tariff, 120, end_status=SessionEndStatus.SYSTEM_FAILURE)
    assert charge.charge_rule == ChargeRule.SYSTEM_FAILURE_NO_CHARGE
    assert (charge.idle_amount, charge.total) == (D("0.00"), D("0.00"))


# Sessão encerrada pelo morador: 50 minutos parado, e mesmo assim a ociosidade sai zero. A energia entregue
# continua sendo cobrada.
def test_sessao_encerrada_pelo_morador_nao_paga_ociosidade(tariff):
    charge = charge_for(tariff, 50, end_status=SessionEndStatus.USER_STOPPED)
    assert charge.charge_rule == ChargeRule.USER_STOPPED_NO_IDLE
    assert charge.idle_amount == D("0.00")
    assert charge.grid_amount > 0  # a energia entregue continua sendo cobrada


# Sem o horário de fim da energia e sem curva de potência, não há como saber quanto tempo o carro ficou
# parado depois da carga. Na dúvida, não se cobra ociosidade, e a memória de cálculo registra a fonte
# desse horário como "unknown" (desconhecida).
def test_sem_fim_de_energia_nao_ha_como_cobrar_ociosidade(tariff):
    session = make_session(energy_ended_at=None, ended_at=at(21, 14))
    charge = calculate_session(session, tariff, [], frozenset(), TZ)
    assert charge.idle_minutes == 0
    assert charge.calculation["components"]["idle"]["energy_end_source"] == "unknown"


# Sem o fim da energia informado, o motor o descobre pela curva: 24 leituras de 7 kW (das 10:00 às 11:55,
# de 5 em 5 minutos) e depois leituras sem fluxo às 12:00 e às 12:15. O fim da energia é 12:00; o carro sai
# às 12:16, então são 16 minutos parado e 1 minuto cobrado. "samples +=" junta mais duas leituras à tupla.
def test_fim_de_energia_estimado_pela_curva(tariff):
    # carga das 10:00 às 11:55 (última leitura com fluxo), sem fluxo às 12:00; carro sai 12:16
    samples = tuple(PowerSample(at(21, 10) + timedelta(minutes=5 * i), D("7")) for i in range(24))
    samples += (PowerSample(at(21, 12), D("0")), PowerSample(at(21, 12, 15), D("0")))
    session = make_session(energy_ended_at=None, ended_at=at(21, 12, 16), power_samples=samples)
    charge = calculate_session(session, tariff, [], frozenset(), TZ)
    assert charge.idle_minutes == 1
    assert charge.calculation["components"]["idle"]["energy_end_source"] == "power_curve"

