"""Testes da fachada check_session (integração das três camadas).

Um teste por porta de saída (passed, ml, rules, structural). Os casos de pico
de 6 kW e 15 kW mostram a divisão de trabalho: 6 kW é possível num carregador
de 7 kW (só o ML estranha); 15 kW é fisicamente impossível (as regras barram).
"""

from condocharge_ai.anomaly import check_session

from tests.test_ml_model import sessao_tipica_do_lab


def test_sessao_tipica_passa_pelas_tres_camadas():
    """Uma sessão típica do lab deve ser aprovada, com a versão do modelo registrada."""
    resultado = check_session(sessao_tipica_do_lab())

    assert resultado["is_anomaly"] is False
    assert resultado["layer"] == "passed"
    assert resultado["model_version"] == "v1.0.0"


def test_pico_atipico_e_barrado_pelo_ml():
    """Uma sessão típica com pico de 6 kW (possível, mas atípico no lab) deve ser barrada pelo ML."""
    dados = sessao_tipica_do_lab()
    dados["max_power_kw"] = 6.0

    resultado = check_session(dados)

    assert resultado["layer"] == "ml"
    assert "LOF_OUTLIER" in resultado["reasons"]


def test_pico_impossivel_e_barrado_pelas_regras():
    """Uma sessão com pico de 15 kW (impossível para um carregador de 7 kW) deve ser barrada pelas regras."""
    dados = sessao_tipica_do_lab()
    dados["max_power_kw"] = 15.0

    resultado = check_session(dados)

    assert resultado["layer"] == "rules"
    assert "POWER_EXCEEDS_NOMINAL" in resultado["reasons"]


def test_campo_ausente_e_barrado_na_validacao():
    """Uma sessão sem o campo de energia deve ser barrada na validação estrutural."""
    dados = sessao_tipica_do_lab()
    del dados["total_kwh"]

    resultado = check_session(dados)

    assert resultado["layer"] == "structural"
    assert "MISSING_FIELD" in resultado["reasons"]