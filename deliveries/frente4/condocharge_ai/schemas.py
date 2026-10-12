"""Camada 1: formato esperado de uma sessão de recarga (validação estrutural com Pydantic)."""

from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class SessionStatus(str, Enum):
    """Lista fechada de status aceitos; qualquer outro texto vira INVALID_FIELD.

    Herdar de str permite comparar o membro direto com texto
    (sessao.status == "completed") e serializar como string no JSON.
    """
    COMPLETED = "completed"
    # Não bloqueia a sessão: aparece em ~12% das sessões reais, inclusive normais
    ABNORMAL_DISCONNECTION = "abnormal_disconnection"
    STOPPED_BY_USER = "stopped_by_user"
    INTERRUPTED_BY_FAILURE = "interrupted_by_failure"


class SessionDTO(BaseModel):
    """Dados de uma sessão de recarga, como o backend recebe da SEMS+.

    O Pydantic converte strings ISO 8601 em datetime e strings numéricas
    em float (ex.: "14.8"); só texto não numérico é rejeitado.
    """
    session_id: str
    charger_id: str
    card_id: str
    started_at: datetime
    ended_at: datetime
    total_kwh: float
    green_kwh: float
    grid_kwh: float
    average_power_kw: float
    max_power_kw: float
    status: SessionStatus
