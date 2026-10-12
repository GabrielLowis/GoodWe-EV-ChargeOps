import datetime
from decimal import Decimal

import pytest

from services.rateio import (Band, Config, billable_idle_minutes, calculate_charge,
                             estimate_idle_minutes, split_segments)

T = datetime.time
D = datetime.datetime

BANDS = [
    Band("Fora de ponta", T(21, 0), T(17, 30), Decimal("0.35"), Decimal("0.60")),
    Band("Intermediaria", T(17, 30), T(18, 0), Decimal("0.45"), Decimal("0.80")),
    Band("Ponta", T(18, 0), T(21, 0), Decimal("0.55"), Decimal("1.10")),
]
CONFIG = Config(Decimal("0.50"), 15, Decimal("5.00"), Decimal("10.00"))


# ---- ociosidade: criterios de aceite do plano (14, 15, 16 min e falha do sistema) ----

@pytest.mark.parametrize("idle,expected", [(14, 0), (15, 0), (16, 1), (30, 15)])
def test_tolerancia_de_15_minutos(idle, expected):
    assert billable_idle_minutes(idle, 15, failed=False) == expected


def test_falha_do_sistema_nao_cobra_ociosidade():
    assert billable_idle_minutes(60, 15, failed=True) == 0


def test_estimativa_de_ociosidade():
    # 14,8 kWh a 7,1 kW = 125,07 min de carga; sessao de 130 min -> 4,93 -> 4 min ociosos (arredonda p/ baixo)
    assert estimate_idle_minutes(14.8, 7.1, D(2026, 9, 22, 19), D(2026, 9, 22, 21, 10)) == 4


# ---- sessao que atravessa faixas tarifarias ----

def test_sessao_dividida_por_faixa():
    # 17:30 -> 20:30: comeca na intermediaria (17:30-18:00) e segue na ponta
    segs = split_segments(D(2026, 9, 22, 17, 30), D(2026, 9, 22, 20, 30), BANDS)
    assert [(s[2].name, s[0].time(), s[1].time()) for s in segs] == [
        ("Intermediaria", T(17, 30), T(18, 0)),
        ("Ponta", T(18, 0), T(20, 30)),
    ]


def test_faixa_que_atravessa_meia_noite():
    segs = split_segments(D(2026, 9, 22, 20, 0), D(2026, 9, 23, 1, 0), BANDS)
    assert [s[2].name for s in segs] == ["Ponta", "Fora de ponta"]
    assert segs[0][1] == D(2026, 9, 22, 21, 0)


def test_valor_e_soma_do_consumo_por_faixa_vezes_tarifa():
    # 3h, 30 kWh (10 grid + 20 green), potencia alta -> sem ociosidade
    # 17:30-18:00 = 1/6 do tempo (Intermediaria); 18:00-20:30 = 5/6 (Ponta)
    r = calculate_charge(started_at=D(2026, 9, 22, 17, 30), ended_at=D(2026, 9, 22, 20, 30),
                         total_kwh=30, green_kwh=20, grid_kwh=10, max_power_kw=11, failed=False,
                         bands=BANDS, config=CONFIG)
    # green: 20/6*0.45 + 20*5/6*0.55 = 1.5 + 9.1667 = 10.67
    # grid : 10/6*0.80 + 10*5/6*1.10 = 1.3333 + 9.1667 = 10.50
    assert r["green_cost"] == Decimal("10.67")
    assert r["grid_cost"] == Decimal("10.50")
    assert [s["band"] for s in r["memory"]["segments"]] == ["Intermediaria", "Ponta"]


def test_formula_subtotal_imposto_overhead():
    r = calculate_charge(started_at=D(2026, 9, 22, 19), ended_at=D(2026, 9, 22, 21, 10),
                         total_kwh=14.8, green_kwh=4.2, grid_kwh=10.6, max_power_kw=7.1, failed=False,
                         bands=BANDS, config=CONFIG)
    assert r["idle_cost"] == Decimal("0.00")           # 5 min < tolerancia
    assert r["subtotal"] == r["green_cost"] + r["grid_cost"] + r["idle_cost"]
    assert r["tax"] == (r["subtotal"] * Decimal("0.05")).quantize(Decimal("0.01"))
    assert r["overhead"] == (r["subtotal"] * Decimal("0.10")).quantize(Decimal("0.01"))
    assert r["total"] == r["subtotal"] + r["tax"] + r["overhead"]


def test_overhead_zero_e_permitido():
    cfg = Config(Decimal("0.50"), 15, Decimal("5.00"), Decimal("0"))
    r = calculate_charge(started_at=D(2026, 9, 22, 19), ended_at=D(2026, 9, 22, 21),
                         total_kwh=10, green_kwh=0, grid_kwh=10, max_power_kw=11, failed=False,
                         bands=BANDS, config=cfg)
    assert r["overhead"] == Decimal("0.00")


def test_ociosidade_cobrada_apos_tolerancia():
    # 2h de sessao, 7 kWh a 7 kW = 60 min de carga -> 60 min ociosos -> cobra 45 min
    r = calculate_charge(started_at=D(2026, 9, 22, 19), ended_at=D(2026, 9, 22, 21),
                         total_kwh=7, green_kwh=0, grid_kwh=7, max_power_kw=7, failed=False,
                         bands=BANDS, config=CONFIG)
    assert r["memory"]["idle"]["billable_minutes"] == 45
    assert r["idle_cost"] == Decimal("22.50")


def test_memoria_de_calculo_reproduz_o_total():
    r = calculate_charge(started_at=D(2026, 9, 22, 17, 30), ended_at=D(2026, 9, 22, 20, 30),
                         total_kwh=30, green_kwh=20, grid_kwh=10, max_power_kw=11, failed=False,
                         bands=BANDS, config=CONFIG)
    comp = r["memory"]["components"]
    assert Decimal(comp["green"]) + Decimal(comp["grid"]) + Decimal(comp["idle"]) == Decimal(comp["subtotal"])
    assert Decimal(comp["subtotal"]) + Decimal(comp["tax"]) + Decimal(comp["overhead"]) == Decimal(comp["total"])


def test_sem_faixa_cobrindo_o_horario_da_erro():
    only_peak = [BANDS[2]]
    with pytest.raises(ValueError):
        calculate_charge(started_at=D(2026, 9, 22, 10), ended_at=D(2026, 9, 22, 11),
                         total_kwh=5, green_kwh=0, grid_kwh=5, max_power_kw=7, failed=False,
                         bands=only_peak, config=CONFIG)
