"""Fachada do modulo de deteccao de anomalias.

O pipeline para na primeira camada que falhar:
  1. estrutural   2. fisica   3. ML (Isolation Forest + LOF)

A camada 3 e do modulo de IA (ai/ml_model.py). Enquanto esse arquivo nao existir,
a camada 3 e ignorada e o score fica None. Contrato esperado do colega:

    def score_session(session) -> tuple[float, bool, list[dict]]
        # (score, suspeita?, [{"code": ..., "message": ...}])
"""
import importlib
from typing import Literal
from pydantic import BaseModel

from ai.rules import layer1_structural, layer2_physical


class AnomalyResult(BaseModel):
    status: Literal["approved", "suspended"]
    layer_failed: int | None = None
    score: float | None = None
    reasons: list[dict] = []


def _ml_module():
    try:
        return importlib.import_module("ai.ml_model")
    except ModuleNotFoundError:
        return None


def check_session(session) -> AnomalyResult:
    reasons = layer1_structural(session)
    if reasons:
        return AnomalyResult(status="suspended", layer_failed=1, reasons=reasons)

    reasons = layer2_physical(session)
    if reasons:
        return AnomalyResult(status="suspended", layer_failed=2, reasons=reasons)

    ml = _ml_module()
    if ml is None:
        return AnomalyResult(status="approved")
    score, suspicious, ml_reasons = ml.score_session(session)
    if suspicious:
        return AnomalyResult(status="suspended", layer_failed=3, score=score, reasons=ml_reasons)
    return AnomalyResult(status="approved", score=score)
