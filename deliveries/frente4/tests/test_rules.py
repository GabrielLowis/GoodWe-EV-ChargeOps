"""Testes da Camada 2 (regras determinísticas de plausibilidade física)."""

from condocharge_ai import rules
from condocharge_ai.schemas import SessionDTO

from tests.test_schemas import dados_sessao_valida


def test_timestamp_valido_passa():
    """Uma sessão que termina depois de começar não deve violar a regra INVALID_TIMESTAMP."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_timestamp(sessao)
    assert resultado is None


def test_timestamp_invalido():
    """Uma sessão que termina antes de começar deve violar a regra INVALID_TIMESTAMP."""
    dados = dados_sessao_valida()
    dados["ended_at"] = "2026-09-22T18:00:00"

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_timestamp(sessao)
    assert resultado == "INVALID_TIMESTAMP"


def test_verificar_kwh_valido():
    """Uma sessão com todas as energias positivas não deve violar a regra NEGATIVE_KWH."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_kwh_negativo(sessao)
    assert resultado is None


def test_verificar_kwh_negativo():
    """Uma sessão com alguma energia negativa (aqui, grid_kwh) deve violar a regra NEGATIVE_KWH."""
    dados = dados_sessao_valida()
    dados["grid_kwh"] = -900

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_kwh_negativo(sessao)
    assert resultado == "NEGATIVE_KWH"


def test_verificar_duracao_normal():
    """Uma sessão com duração acima de 1 minuto não deve violar a regra DURATION_TOO_SHORT."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_duracao_curta(sessao)
    assert resultado is None


def test_verificar_duracao_curta():
    """Uma sessão com menos de 1 minuto e energia registrada deve violar a regra DURATION_TOO_SHORT."""
    dados = dados_sessao_valida()
    dados["ended_at"] = "2026-09-22T19:00:30"

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_duracao_curta(sessao)
    assert resultado == "DURATION_TOO_SHORT"


def test_carregador_conhecido_passa():
    """Uma sessão com carregador cadastrado não deve violar a regra UNKNOWN_CHARGER."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_carregador_conhecido(sessao)
    assert resultado is None


def test_carregador_desconhecido_e_detectado():
    """Uma sessão com carregador não cadastrado deve violar a regra UNKNOWN_CHARGER."""
    dados = dados_sessao_valida()
    dados["charger_id"] = "HCA99"

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_carregador_conhecido(sessao)
    assert resultado == "UNKNOWN_CHARGER"


def test_potencia_dentro_do_nominal_passa():
    """Uma sessão com potência dentro da margem do nominal não deve violar a regra POWER_EXCEEDS_NOMINAL."""
    dados = dados_sessao_valida()  # max_power_kw=7.1, dentro da tolerância de 7.35
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_potencia(sessao)
    assert resultado is None


def test_potencia_acima_do_nominal_e_detectada():
    """Uma sessão com potência acima do nominal do carregador deve violar a regra POWER_EXCEEDS_NOMINAL."""
    dados = dados_sessao_valida()
    dados["max_power_kw"] = 15.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_potencia(sessao)
    assert resultado == "POWER_EXCEEDS_NOMINAL"


def test_energia_dentro_da_capacidade_passa():
    """Uma sessão com energia compatível com potência e duração não deve violar a regra KWH_EXCEEDS_CAPACITY."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_capacidade(sessao)
    assert resultado is None


def test_energia_acima_da_capacidade_e_detectada():
    """Uma sessão com mais energia do que o carregador consegue entregar no período deve violar a regra KWH_EXCEEDS_CAPACITY."""
    dados = dados_sessao_valida()
    dados["total_kwh"] = 50.0  # máximo físico em 2h10 a 7 kW é ~15,9 kWh

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_capacidade(sessao)
    assert resultado == "KWH_EXCEEDS_CAPACITY"


def test_atribuicao_de_energia_coerente_passa():
    """Uma sessão em que solar + rede explica o total não deve violar a regra ENERGY_SOURCE_ATTRIBUTION_MISMATCH."""
    dados = dados_sessao_valida()  # 4.2 + 10.6 = 14.8
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_atribuicao_energia(sessao)
    assert resultado is None


def test_atribuicao_de_energia_incoerente_e_detectada():
    """Uma sessão com origens zeradas e total positivo (padrão observado na SEMS+) deve violar a regra ENERGY_SOURCE_ATTRIBUTION_MISMATCH."""
    dados = dados_sessao_valida()
    dados["green_kwh"] = 0.0
    dados["grid_kwh"] = 0.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_atribuicao_energia(sessao)
    assert resultado == "ENERGY_SOURCE_ATTRIBUTION_MISMATCH"


def test_sessao_plausivel_nao_viola_nenhuma_regra():
    """Uma sessão plausível deve passar por todas as regras sem violações."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_regras(sessao)
    assert resultado == []


def test_sessao_com_varios_problemas_retorna_todas_as_violacoes():
    """Uma sessão com mais de um problema deve ter todas as violações listadas."""
    dados = dados_sessao_valida()
    dados["grid_kwh"] = -900
    dados["max_power_kw"] = 15.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_regras(sessao)
    # "in" em vez de igualdade: grid negativo também quebra a atribuição de
    # energia, então a lista tem mais códigos além destes dois
    assert "NEGATIVE_KWH" in resultado
    assert "POWER_EXCEEDS_NOMINAL" in resultado


def test_atribuicao_com_arredondamento_em_sessao_pequena_passa():
    """Uma sessão pequena com green arredondado a uma casa decimal não deve violar a regra ENERGY_SOURCE_ATTRIBUTION_MISMATCH."""
    dados = dados_sessao_valida()
    dados["total_kwh"] = 0.75
    dados["green_kwh"] = 0.7  # SEMS mostra uma casa decimal
    dados["grid_kwh"] = 0.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_atribuicao_energia(sessao)
    assert resultado is None


def test_sessao_com_energia_passa_na_regra_sem_energia():
    """Uma sessão com energia entregue não deve violar a regra NO_ENERGY_DELIVERED."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_sem_energia(sessao)
    assert resultado is None


def test_sessao_sem_energia_e_detectada():
    """Uma sessão sem energia entregue (carro plugado sem carregar) deve violar a regra NO_ENERGY_DELIVERED."""
    dados = dados_sessao_valida()
    dados["green_kwh"] = 0.0
    dados["grid_kwh"] = 0.0
    dados["total_kwh"] = 0.0

    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_sem_energia(sessao)
    assert resultado == "NO_ENERGY_DELIVERED"


def test_sessao_no_limite_de_energia_e_detectada():
    """Uma sessão com exatamente 0,25 kWh deve violar a regra NO_ENERGY_DELIVERED (a comparação usa <=)."""
    dados = dados_sessao_valida()
    dados["total_kwh"] = 0.25
    dados["green_kwh"] = 0.25
    dados["grid_kwh"] = 0.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_sem_energia(sessao)
    assert resultado == "NO_ENERGY_DELIVERED"


def test_sessao_logo_acima_do_limite_passa():
    """Uma sessão com 0,26 kWh, logo acima do limite, não deve violar a regra NO_ENERGY_DELIVERED."""
    dados = dados_sessao_valida()
    dados["total_kwh"] = 0.26
    dados["green_kwh"] = 0.26
    dados["grid_kwh"] = 0.0

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_sem_energia(sessao)
    assert resultado is None


def test_potencia_media_abaixo_da_maxima_passa():
    """Uma sessão com potência média abaixo da máxima não deve violar a regra AVERAGE_EXCEEDS_MAX_POWER."""
    dados = dados_sessao_valida()  # média 6,8 kW, máxima 7,1 kW
    sessao = SessionDTO.model_validate(dados)
    resultado = rules.verificar_potencia_media_acima_da_maxima(sessao)
    assert resultado is None


def test_potencia_media_acima_da_maxima_e_detectada():
    """Uma sessão com potência média maior que a máxima deve violar a regra AVERAGE_EXCEEDS_MAX_POWER."""
    dados = dados_sessao_valida()
    dados["average_power_kw"] = 7.1
    dados["max_power_kw"] = 6.8

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_potencia_media_acima_da_maxima(sessao)
    assert resultado == "AVERAGE_EXCEEDS_MAX_POWER"


def test_potencia_media_igual_a_maxima_passa():
    """Uma sessão com potência média igual à máxima não deve violar a regra AVERAGE_EXCEEDS_MAX_POWER (a comparação usa >)."""
    dados = dados_sessao_valida()
    dados["average_power_kw"] = 7.1
    dados["max_power_kw"] = 7.1

    sessao = SessionDTO.model_validate(dados)

    resultado = rules.verificar_potencia_media_acima_da_maxima(sessao)
    assert resultado is None