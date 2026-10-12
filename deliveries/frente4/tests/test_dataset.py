"""Testes do gerador de sessões sintéticas."""

from condocharge_ai import rules
from condocharge_ai.schemas import SessionDTO
from condocharge_ai.training import dataset


def test_sessoes_geradas_sao_plausiveis():
    """Toda sessão gerada deve passar pelas Camadas 1 e 2 sem violações."""
    sessoes = dataset.gerar_sessoes_normais(200)

    assert len(sessoes) == 200
    for dados in sessoes:
        sessao = SessionDTO.model_validate(dados)
        assert rules.verificar_regras(sessao) == []


def test_anomalias_passam_nas_regras_fisicas():
    """As anomalias devem ser fisicamente possíveis, para que apenas a Camada 3 possa detectá-las."""
    bases = dataset.gerar_sessoes_normais(8)
    anomalias = dataset.criar_anomalias(bases)

    assert len(anomalias) == len(dataset.TIPOS_ANOMALIA) * 8
    for dados in anomalias:
        sessao = SessionDTO.model_validate(dados)
        assert rules.verificar_regras(sessao) == []