"""Regras determinísticas da Camada 2: plausibilidade física das sessões.

Cada regra devolve um código de violação ou None. Violação aqui é certeza
(não suspeita estatística), por isso a fachada dá score 1.0 a ela. Quase todas
são impossibilidades físicas; a exceção é NO_ENERGY_DELIVERED, um evento real
(carro plugado sem carregar) que também não deve entrar no rateio de energia.
"""

from condocharge_ai.schemas import SessionDTO

# Potência nominal (kW) de cada carregador cadastrado no condomínio.
# Dicionário (e não constante única) para atender prédios com vários
# carregadores de potências diferentes. É o limite físico do equipamento,
# não o teto de operação observado no lab (3,3 a 3,5 kW), que fica com o ML.
POTENCIA_NOMINAL_KW = {
    "HCA01": 7.0,
}

# Duração mínima (s) para uma sessão com energia registrada ser plausível.
DURACAO_MINIMA_SEGUNDOS = 60

# Margem para variações normais de medição (5%).
# Margem de segurança, não valor calibrado: medidores oscilam um pouco acima do
# nominal, e a regra só deve barrar o claramente impossível (no lab o pico
# nunca passou de 3,5 kW, longe dos 7,35 kW). A mesma margem vale para a regra
# de capacidade, que usa a potência nominal.
TOLERANCIA_POTENCIA = 0.05
TOLERANCIA_ATRIBUICAO = 0.05


# Piso da tolerância (kWh): a SEMS mostra o green com uma casa decimal.
# Sem ele, sessões pequenas eram barradas à toa (ex.: green 0,7 de 0,75 kWh,
# diferença acima dos 5% do total).
TOLERANCIA_ATRIBUICAO_MIN_KWH = 0.1

# Energia máxima (kWh) de uma sessão sem recarga: as sessões reais sem energia tiveram até 0,24 kWh, e a menor sessão normal real teve 0,75 kWh
# Precisa ficar abaixo das anomalias de avaliação, que só o ML deve detectar.
# Esta mesma constante é usada em training/dados_reais.py para separar as sessões sem recarga
# mesmas sessões com outro valor.
ENERGIA_MINIMA_RECARGA_KWH = 0.25


def verificar_timestamp(sessao: SessionDTO):
    """Detecta sessão que termina antes ou no mesmo instante em que começou."""
    if sessao.ended_at <= sessao.started_at:
        return "INVALID_TIMESTAMP"
    return None


def verificar_kwh_negativo(sessao: SessionDTO):
    """Detecta qualquer energia (total, solar ou rede) negativa."""
    if sessao.total_kwh < 0 or sessao.grid_kwh < 0 or sessao.green_kwh < 0:
        return "NEGATIVE_KWH"
    return None


def verificar_duracao_curta(sessao: SessionDTO):
    """Detecta sessão com menos de 1 minuto que mesmo assim registrou energia."""
    duracao = (sessao.ended_at - sessao.started_at).total_seconds()
    # Sessão curta sem energia (plugou e desplugou) é comportamento normal, não erro de medição;
    # quem a sinaliza é NO_ENERGY_DELIVERED
    if duracao < DURACAO_MINIMA_SEGUNDOS and sessao.total_kwh > 0:
        return "DURATION_TOO_SHORT"
    return None


def verificar_carregador_conhecido(sessao: SessionDTO):
    """Detecta sessão de um carregador que não está cadastrado."""
    if sessao.charger_id not in POTENCIA_NOMINAL_KW:
        return "UNKNOWN_CHARGER"
    return None


def verificar_potencia(sessao: SessionDTO):
    """Detecta potência máxima acima da nominal do carregador (com tolerância)."""
    if sessao.charger_id not in POTENCIA_NOMINAL_KW:
        return None  # caso já tratado pela regra UNKNOWN_CHARGER

    nominal = POTENCIA_NOMINAL_KW[sessao.charger_id]
    limite = nominal * (1 + TOLERANCIA_POTENCIA)

    if sessao.max_power_kw > limite:
        return "POWER_EXCEEDS_NOMINAL"
    return None


def verificar_capacidade(sessao: SessionDTO):
    """Detecta energia acima do máximo que o carregador entrega no tempo da sessão."""
    if sessao.charger_id not in POTENCIA_NOMINAL_KW:
        return None  # caso já tratado pela regra UNKNOWN_CHARGER

    duracao_horas = (sessao.ended_at - sessao.started_at).total_seconds() / 3600
    if duracao_horas <= 0:
        return None  # caso já tratado pela regra INVALID_TIMESTAMP

    nominal = POTENCIA_NOMINAL_KW[sessao.charger_id]
    capacidade_kwh = nominal * duracao_horas * (1 + TOLERANCIA_POTENCIA)

    if sessao.total_kwh > capacidade_kwh:
        return "KWH_EXCEEDS_CAPACITY"
    return None


def verificar_atribuicao_energia(sessao: SessionDTO):
    """Detecta quando solar (green) + rede (grid) não explica o total consumido.

    Dispara no lab quando a SEMS zera as duas origens. A regra fica ativa de
    propósito: sem origem confiável, o rateio solar/rede da sessão sairia errado.
    """
    soma_origens = sessao.green_kwh + sessao.grid_kwh
    diferenca = abs(soma_origens - sessao.total_kwh)

    tolerancia = max(sessao.total_kwh * TOLERANCIA_ATRIBUICAO, TOLERANCIA_ATRIBUICAO_MIN_KWH)
    if diferenca > tolerancia:
        return "ENERGY_SOURCE_ATTRIBUTION_MISMATCH"
    return None


def verificar_sem_energia(sessao: SessionDTO):
    """Detecta sessão em que o carro ficou plugado sem receber energia.

    Antes desta regra, 7 das 10 sessões reais sem energia caíam no ML e o
    síndico via só "padrão fora do histórico". Aqui elas chegam com o motivo
    certo, útil para a tarifa de ociosidade do rateio.
    """
    # "<=": o limite é o próprio teto das sessões sem recarga
    if sessao.total_kwh <= ENERGIA_MINIMA_RECARGA_KWH:
        return "NO_ENERGY_DELIVERED"
    return None


def verificar_potencia_media_acima_da_maxima(sessao: SessionDTO):
    """Detecta sessão com potência média maior que a máxima, o que é fisicamente impossível."""
    # Usa > e não >=: média igual à máxima é possível (sessão sem energia ou carga plana)
    if sessao.average_power_kw > sessao.max_power_kw:
        return "AVERAGE_EXCEEDS_MAX_POWER"
    return None

# Ordem em que as regras são aplicadas. Para criar uma regra nova, basta escrever a função acima e acrescentá-la nesta lista.
# A lista guarda as próprias funções (sem parênteses), que verificar_regras chama uma a uma.
REGRAS = [
    verificar_timestamp,
    verificar_kwh_negativo,
    verificar_duracao_curta,
    verificar_carregador_conhecido,
    verificar_potencia,
    verificar_capacidade,
    verificar_atribuicao_energia,
    verificar_sem_energia,
    verificar_potencia_media_acima_da_maxima,
]


def verificar_regras(sessao: SessionDTO):
    """Aplica todas as regras e devolve a lista de códigos violados (vazia se a sessão é plausível).

    Não para na primeira violação: o síndico vê todos os problemas de uma vez.
    """
    violacoes = []
    for regra in REGRAS:
        codigo = regra(sessao)
        if codigo is not None:
            violacoes.append(codigo)
    return violacoes