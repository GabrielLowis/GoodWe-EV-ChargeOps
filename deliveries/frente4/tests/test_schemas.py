"""Testes da Camada 1 (validação estrutural) do módulo de IA do CondoCharge."""

import pytest
from pydantic import ValidationError

from condocharge_ai.schemas import SessionDTO


def dados_sessao_valida():
    """Dados de uma sessão de recarga válida, usados como base nos testes."""
    # Função, e não constante: cada teste recebe um dicionário novo e pode
    # alterá-lo sem afetar os outros
    return {
        "session_id": "abc123",
        "charger_id": "HCA01",
        "card_id": "RFID-05",
        "started_at": "2026-09-22T19:00:00",
        "ended_at": "2026-09-22T21:10:00",
        "total_kwh": 14.8,
        "green_kwh": 4.2,
        "grid_kwh": 10.6,
        "average_power_kw": 6.8,
        "max_power_kw": 7.1,
        "status": "completed",
    }


def test_sessao_valida_e_criada():
    """Uma sessão com todos os campos corretos deve ser aceita pelo SessionDTO."""
    # Cenário: dados de uma sessão normal
    dados = dados_sessao_valida()
    sessao = SessionDTO.model_validate(dados)
    
    # Verificação: os valores ficaram guardados corretamente
    assert sessao.total_kwh == 14.8
    # SessionStatus herda de str, então o membro do Enum pode ser comparado com texto
    assert sessao.status == "completed"


def test_total_kwh_texto_e_rejeitado():
    """Uma sessão com total_kwh em texto deve ser rejeitada pelo SessionDTO."""
    # Cenário: sessão válida em tudo, exceto total_kwh com texto no lugar de número
    dados = dados_sessao_valida()
    dados["total_kwh"] = "muito"

    # Verificação: a validação deve falhar
    with pytest.raises(ValidationError):
        SessionDTO.model_validate(dados)


def test_status_invalido_e_rejeitado():
    """Uma sessão com status fora da lista permitida deve ser rejeitada pelo SessionDTO."""
    # Cenário: sessão válida em tudo, exceto status
    dados = dados_sessao_valida()
    dados["status"] = "HSIUAKO"

    # Verificação: a validação deve falhar
    with pytest.raises(ValidationError):
        SessionDTO.model_validate(dados)