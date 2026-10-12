"""Distribuição dos kWh entre trechos (sem banco)."""

# Como ler este arquivo:
# - O medidor diz quantos kWh foram entregues na sessão inteira, mas não em cada faixa. O allocation.py
#   estima a fatia de cada trecho: pela curva de potência, quando existe, ou pelo tempo.
# - split_quantity divide um total em partes proporcionais aos "pesos", fechando sempre a soma exata.
# - D("7.500") é um Decimal (número decimal exato); D(30) também, criado a partir de um inteiro.
# - at(21, 10) = 21/09/2026 às 10:00, no fuso do condomínio.

from datetime import timedelta
from decimal import Decimal as D

from backend.rateio.allocation import (
    METHOD_POWER_CURVE,
    METHOD_TIME,
    allocation_weights,
    derive_energy_end,
    energy_between,
    split_quantity,
    time_weights,
)
from backend.rateio.bands import split_by_band
from backend.rateio.models import PowerSample
from backend.tests.helpers import TZ, at


# Monta uma curva de potência de teste: uma leitura a cada `step` minutos a partir de `start`, com as
# potências da lista (em kW). Ex.: curve(at(21, 10), ["6", "6", "0"]) = 6 kW às 10:00 e às 10:05, 0 às 10:10.
# green é opcional: a parte solar de cada leitura. "D(green[i]) if green else None" usa o valor solar da
# mesma posição quando a lista existe, e None quando não existe.
def curve(start, values, step=5, green=None):
    return [
        PowerSample(start + timedelta(minutes=i * step), D(v), D(green[i]) if green else None)
        for i, v in enumerate(values)
    ]


# --- Método dos maiores restos -------------------------------------------------------------
# 7,500 kWh divididos na proporção 30:40. As partes exatas seriam 3,2142... e 4,2857...; cortando cada uma
# no Wh inteiro (3,214 e 4,285), a soma daria 7,499 e sobraria 1 Wh. O método dos maiores restos dá esse
# Wh à maior fração (a segunda, 0,71 contra 0,29), e a soma fecha exatamente em 7,500.
def test_divisao_fecha_exatamente_com_o_total():
    parts = split_quantity(D("7.500"), [D(30), D(40)])
    assert parts == [D("3.214"), D("4.286")]
    assert sum(parts) == D("7.500")


# 10 kWh em três partes iguais: 3,333 x 3 = 9,999 e sobra 1 Wh. Os três restos empatam, e o desempate
# manda o Wh para o trecho mais antigo (o primeiro).
def test_maiores_restos_empate_vai_para_o_trecho_mais_antigo():
    assert split_quantity(D("10.000"), [D(1), D(1), D(1)]) == [D("3.334"), D("3.333"), D("3.333")]


# Pesos todos zero não dizem nada sobre a proporção: a energia inteira fica no primeiro trecho, em vez de
# sumir ou dar erro de divisão por zero.
def test_sem_pesos_toda_energia_vai_para_o_primeiro_trecho():
    assert split_quantity(D("2.000"), [D(0), D(0)]) == [D("2.000"), D("0")]


# --- Pesos por tempo e por curva -----------------------------------------------------------
# Sem curva, o peso de cada trecho é a sua duração em segundos: 30 min (1800 s) no intermediário e
# 150 min (9000 s) na ponta, ou seja, 1 para 5.
def test_pesos_por_tempo_no_exemplo_do_plano(tariff):
    segments = split_by_band(at(21, 17, 30), at(21, 20, 30), tariff, frozenset(), TZ)
    assert time_weights(segments) == [D(1800), D(9000)]  # 30 min e 150 min -> 1:5


# Energia = área embaixo da curva de potência. Com 7 kW constantes durante 1 hora, a área é 7 kWh.
def test_integral_de_potencia_constante():
    samples = curve(at(21, 10), ["7", "7"], step=60)
    assert energy_between(samples, at(21, 10), at(21, 11)) == D(7)


# Potência subindo em linha reta de 0 a 6 kW em 1 hora: a área é um triângulo, (0 + 6) / 2 x 1 h = 3 kWh.
# Na primeira meia hora a potência vai de 0 a 3 kW: (0 + 3) / 2 x 0,5 h = 0,75 kWh. A regra do trapézio
# acerta essas contas em cheio, porque entre duas leituras ela supõe justamente uma reta.
def test_integral_de_rampa_linear_e_exata():
    samples = curve(at(21, 10), ["0", "6"], step=60)  # 0 -> 6 kW em 1 h = 3 kWh
    assert energy_between(samples, at(21, 10), at(21, 11)) == D(3)
    assert energy_between(samples, at(21, 10), at(21, 10, 30)) == D("0.75")


# A curva do exemplo do plano (37 leituras de 5 em 5 minutos, com a potência caindo no fim). Como a queda
# acontece na ponta, a ponta fica com menos do que os 5/6 que a divisão por tempo daria (cerca de 82%).
# allocation_weights devolve três coisas (pesos Green, pesos Grid e o método), recebidas de uma vez.
def test_curva_com_queda_no_final_reduz_a_fatia_da_ponta(tariff):
    start, end = at(21, 17, 30), at(21, 20, 30)
    segments = split_by_band(start, end, tariff, frozenset(), TZ)
    samples = curve(start, ["6.6"] + ["6.9"] * 30 + ["6.0", "5.0", "4.0", "3.0", "2.0", "0.0"])
    green_w, grid_w, method = allocation_weights(segments, samples, start, end)
    assert method == METHOD_POWER_CURVE
    peak_share = grid_w[1] / sum(grid_w)
    assert peak_share < D(5) / D(6)  # por tempo seria 5/6; a queda final reduz a ponta


# A curva só vale se cobrir pelo menos 90% da carga. Aqui são 3 leituras de 10 em 10 minutos, que cobrem
# só 20 dos 180 minutos: o motor desconfia da curva e divide pelo tempo. O "_" descarta os valores que o
# teste não usa.
def test_curva_que_cobre_pouco_da_sessao_cai_para_o_tempo(tariff):
    start, end = at(21, 17, 30), at(21, 20, 30)
    segments = split_by_band(start, end, tariff, frozenset(), TZ)
    samples = curve(start, ["7", "7", "7"], step=10)  # cobre só 20 de 180 min
    _, _, method = allocation_weights(segments, samples, start, end)
    assert method == METHOD_TIME


# Quando cada leitura informa também a parte solar, Green e Grid são divididos cada um pela sua própria
# curva. Aqui o sol cai de 7 kW para 0 entre 17:30 e 18:00 (intermediário) e fica em 0 na ponta.
def test_curva_com_parcela_solar_por_instante_separa_green_e_grid(tariff):
    # 17:30-18:30: sol só na primeira meia hora (intermediário)
    start, end = at(21, 17, 30), at(21, 18, 30)
    segments = split_by_band(start, end, tariff, frozenset(), TZ)
    samples = curve(start, ["7", "7", "7"], step=30, green=["7", "0", "0"])
    green_w, grid_w, _ = allocation_weights(segments, samples, start, end)
    green_parts = split_quantity(D("2.000"), green_w)
    assert green_parts[0] > green_parts[1]  # a energia solar cai toda no trecho intermediário
    assert grid_w[1] > grid_w[0]


# --- Fim do fluxo de energia pela curva ----------------------------------------------------
# Leituras 6, 6, 1,5, 0, 0 kW às 10:00, 10:05, 10:10, 10:15 e 10:20. A última com fluxo (acima de 0,1 kW)
# é a das 10:10; a primeira sem fluxo depois dela é a das 10:15, e é esse o fim da energia.
def test_fim_da_energia_e_a_primeira_leitura_sem_fluxo():
    samples = curve(at(21, 10), ["6", "6", "1.5", "0", "0"])
    assert derive_energy_end(samples, at(21, 10, 30)) == at(21, 10, 15)


# A curva termina ainda com 6 kW: não dá para provar que a carga acabou antes da desconexão (10:30).
# Na dúvida, a favor do morador: o fim da energia é a própria desconexão, e não há ociosidade.
def test_curva_terminando_com_fluxo_nao_prova_ociosidade():
    samples = curve(at(21, 10), ["6", "6", "6"])
    assert derive_energy_end(samples, at(21, 10, 30)) == at(21, 10, 30)


# Uma curva que nunca teve fluxo não diz quando a energia parou: o resultado é None ("não sei").
def test_curva_sem_fluxo_nao_informa_fim():
    assert derive_energy_end(curve(at(21, 10), ["0", "0"]), at(21, 10, 30)) is None

