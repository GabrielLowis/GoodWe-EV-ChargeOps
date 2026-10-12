"""Geração de sessões sintéticas calibradas com as sessões reais do HCA G2 (SEMS+).

O modelo é treinado com dado real, não com estas sessões. O gerador serve aos
testes automatizados (que não dependem dos CSVs) e como plano B para
condomínios sem histórico. Também cria as anomalias usadas na avaliação.
"""

from datetime import datetime, timedelta

import numpy as np

# Energia por sessão (kWh): 215 sessões reais da SEMS+ (out/2025 a out/2026)
ENERGIA_MEDIA_KWH = 8.0
ENERGIA_DESVIO_KWH = 3.4

# Potência média (kW): cresce com a energia da sessão (correlação 0,39 nas sessões reais)
# Com a energia média de 8 kWh dá ~2,3 kW (1,86 + 0,05 x 8). A estimativa inicial
# de 3,0 kW vinha de só duas sessões; com 215 ficou claro que o carregador reduz
# a potência no fim da carga.
POTENCIA_BASE_KW = 1.86
POTENCIA_POR_KWH = 0.05
POTENCIA_DESVIO_KW = 0.40

# Fração do tempo da sessão em que o carro efetivamente carrega.
# É o mesmo fator de coerência das sessões reais (0,90 ± 0,008), por isso a
# duração gerada fecha a conta energia = potência média x duração x 0,9.
FRACAO_TEMPO_CARREGANDO = 0.9

# Potência máxima (kW): teto de operação do carregador do lab
# (bem abaixo dos 7 kW nominais; nas sessões reais o pico ficou entre 3,3 e 3,5)
POTENCIA_MAXIMA_MIN_KW = 3.3
POTENCIA_MAXIMA_MAX_KW = 3.5

# Horário de início: dois grupos observados nas sessões reais.
# Só dá realismo às datas geradas; a hora não é feature do modelo.
PROPORCAO_SESSOES_NOITE = 0.88
HORA_NOITE_MEDIA = 20.8
HORA_NOITE_DESVIO = 1.3
HORA_DIA_MEDIA = 14.0
HORA_DIA_DESVIO = 3.0


def gerar_sessao_normal(rng, indice):
    """Gera uma sessão de recarga normal, no formato do SessionDTO."""
    # A normal pode sortear valores fora do que é físico ou do que o lab mostra;
    # os max/min cortam as pontas: energia >= 1 kWh (até 0,25 kWh nem é recarga (limite da regra NO_ENERGY_DELIVERED)),
    # hora dentro do dia e potência média entre 1,0 e 3,3 kW (faixa real).
    energia_kwh = max(rng.normal(ENERGIA_MEDIA_KWH, ENERGIA_DESVIO_KWH), 1.0)
    if rng.uniform(0.0, 1.0) < PROPORCAO_SESSOES_NOITE:
        hora_sorteada = rng.normal(HORA_NOITE_MEDIA, HORA_NOITE_DESVIO)
    else:
        hora_sorteada = rng.normal(HORA_DIA_MEDIA, HORA_DIA_DESVIO)
    hora_inicio = min(max(hora_sorteada, 0.0), 23.5)
    potencia_sorteada = POTENCIA_BASE_KW + POTENCIA_POR_KWH * energia_kwh + rng.normal(0.0, POTENCIA_DESVIO_KW)
    potencia_media_kw = min(max(potencia_sorteada, 1.0), 3.3)

    data_base = datetime(2026, 9, 1)
    dia = int(rng.integers(0, 30))
    inicio = data_base + timedelta(days=dia, hours=hora_inicio)
    duracao_horas = energia_kwh / potencia_media_kw / FRACAO_TEMPO_CARREGANDO
    fim = inicio + timedelta(hours=duracao_horas)

    potencia_maxima_kw = rng.uniform(POTENCIA_MAXIMA_MIN_KW, POTENCIA_MAXIMA_MAX_KW)
    # Divisão solar/rede aleatória (não imita o lab, que registra quase tudo como
    # green): basta que green + grid feche o total para passar na regra de atribuição
    fracao_green = rng.uniform(0.0, 1.0)
    green_kwh = energia_kwh * fracao_green
    grid_kwh = energia_kwh - green_kwh

    return {
        "session_id": f"SIM-{indice:04d}",
        "charger_id": "HCA01",
        "card_id": "SIM-CARD",
        "started_at": inicio,
        "ended_at": fim,
        "total_kwh": round(energia_kwh, 2),
        "green_kwh": round(green_kwh, 2),
        "grid_kwh": round(grid_kwh, 2),
        "average_power_kw": round(potencia_media_kw, 2),
        "max_power_kw": round(potencia_maxima_kw, 2),
        "status": "completed",
    }


def gerar_sessoes_normais(quantidade, semente=42):
    """Gera múltiplas sessões de recarga normal, no formato do SessionDTO."""
    # Um único gerador com semente fixa: a mesma chamada sempre devolve as mesmas
    # sessões, o que mantém os testes reproduzíveis
    rng = np.random.default_rng(semente)
    sessoes = []
    for i in range(quantidade):
        sessoes.append(gerar_sessao_normal(rng, i))
    return sessoes


# Tipos de anomalia de medição usados para avaliar o modelo.
# Todas são fisicamente possíveis (passam nas regras), mas destoam do padrão real do lab.
TIPOS_ANOMALIA = [
    "pico_alto",
    "potencia_alta",
    "energia_alta",
    "lenta",
    "medicao_incoerente",
]


def criar_anomalia(base, tipo, indice):
    """Cria uma anomalia de medição a partir de uma sessão normal, sem violar as regras físicas."""
    dados = dict(base)  # cópia: a sessão original não pode ser alterada
    # O prefixo ANOM-{tipo}- é usado pelo avaliar.py para contar a detecção por tipo
    dados["session_id"] = f"ANOM-{tipo}-{indice:02d}"
    # A base pode vir do CSV real (texto) ou do gerador (datetime); str() + fromisoformat
    # aceita os dois
    inicio = datetime.fromisoformat(str(base["started_at"]))

    if tipo == "pico_alto":
        # Pico de 6 kW: abaixo do limite físico, mas o real nunca passou de 3,5 kW
        dados["max_power_kw"] = 6.0

    elif tipo == "potencia_alta":
        # Média de 5 kW: o real nunca passou de 3,4 kW. A duração encolhe para fechar a conta
        dados["average_power_kw"] = 5.0
        dados["max_power_kw"] = 6.0
        duracao_horas = base["total_kwh"] / 5.0 / FRACAO_TEMPO_CARREGANDO
        dados["ended_at"] = inicio + timedelta(hours=duracao_horas)

    elif tipo == "energia_alta":
        # Energia bem acima da maior sessão real (16 kWh), com duração coerente
        # (o "+ 5" afasta as bases pequenas do normal; com as bases de validação
        # o mínimo gerado é ~17 kWh, mas uma base abaixo de ~4,5 kWh ficaria sob 16)
        dados["total_kwh"] = round(base["total_kwh"] * 2.5 + 5.0, 2)
        duracao_horas = dados["total_kwh"] / base["average_power_kw"] / FRACAO_TEMPO_CARREGANDO
        dados["ended_at"] = inicio + timedelta(hours=duracao_horas)

    elif tipo == "lenta":
        # Média de 0,5 kW: o real nunca ficou abaixo de 1,0 kW
        dados["average_power_kw"] = 0.5
        duracao_horas = base["total_kwh"] / 0.5 / FRACAO_TEMPO_CARREGANDO
        dados["ended_at"] = inicio + timedelta(hours=duracao_horas)

    elif tipo == "medicao_incoerente":
        # Energia registrada em 30% do que potência x tempo indicam: os números não conversam
        # (fator de coerência cai de ~0,90 para ~0,27; é essa feature que denuncia o caso)
        dados["total_kwh"] = round(base["total_kwh"] * 0.3, 2)

    else:
        raise ValueError(f"Tipo de anomalia desconhecido: {tipo}")

    # Atribuição coerente com o padrão do lab (toda energia registrada como green)
    dados["green_kwh"] = dados["total_kwh"]
    dados["grid_kwh"] = 0.0
    return dados


def criar_anomalias(sessoes_base, por_tipo=8):
    """Aplica cada tipo de anomalia sobre as primeiras sessões da lista base.

    Com as 43 sessões de validação e por_tipo=8: 5 tipos x 8 = 40 anomalias.
    """
    anomalias = []
    for tipo in TIPOS_ANOMALIA:
        for indice, base in enumerate(sessoes_base[:por_tipo]):
            anomalias.append(criar_anomalia(base, tipo, indice))
    return anomalias