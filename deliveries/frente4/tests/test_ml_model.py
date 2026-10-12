"""Testes da Camada 3 (modelo de detecção de anomalias).

Usam o modelo salvo em artifacts/modelo_v1.joblib: se o modelo for retreinado,
estes testes também verificam se o comportamento esperado se manteve.
"""

import pytest

from condocharge_ai import ml_model
from condocharge_ai.schemas import SessionDTO

from tests.test_schemas import dados_sessao_valida


def test_features_extraidas_na_ordem_esperada():
    """A sessão padrão (2h10, 14,8 kWh) deve virar o vetor de features esperado."""
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    features = ml_model.extrair_features(sessao)

    assert len(features) == len(ml_model.NOMES_FEATURES)
    assert features[0] == pytest.approx(2.1667, abs=0.001)
    assert features[1] == 14.8
    assert features[2] == 6.8
    assert features[3] == 7.1
    # 14,8 / (6,8 x 2,1667): acima do ~0,90 real porque a sessão padrão é hipotética
    assert features[4] == pytest.approx(1.0045, abs=0.001)


def sessao_tipica_do_lab():
    """Sessão com valores próximos da mediana das sessões reais do HCA G2."""
    # A sessão padrão de test_schemas (6,8 kW de média) serve às regras, mas está
    # longe do perfil do lab; para o ML a base precisa ser típica: 8 kWh, 2,3 kW de
    # média, pico de 3,4 kW e fator de coerência ~0,91. Também é usada em test_anomaly.
    dados = dados_sessao_valida()
    dados["started_at"] = "2026-09-22T21:00:00"
    dados["ended_at"] = "2026-09-23T00:50:00"
    dados["total_kwh"] = 8.0
    dados["green_kwh"] = 8.0
    dados["grid_kwh"] = 0.0
    dados["average_power_kw"] = 2.3
    dados["max_power_kw"] = 3.4
    return dados


def test_sessao_tipica_nao_e_anomala():
    """Uma sessão com a cara das sessões reais do lab não deve ser marcada pela Camada 3."""
    sessao = SessionDTO.model_validate(sessao_tipica_do_lab())
    resultado = ml_model.avaliar_sessao(sessao)
    assert resultado["is_anomaly"] is False
    assert resultado["reasons"] == []


def test_pico_de_potencia_atipico_e_anomalo():
    """Uma sessão típica com pico de 6 kW (o lab nunca passa de 3,5 kW) deve ser marcada pela Camada 3."""
    dados = sessao_tipica_do_lab()
    dados["max_power_kw"] = 6.0
    sessao = SessionDTO.model_validate(dados)
    resultado = ml_model.avaliar_sessao(sessao)
    assert resultado["is_anomaly"] is True
    assert resultado["model_version"] == "v1.0.0"

