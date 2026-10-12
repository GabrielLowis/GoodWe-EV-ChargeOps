"""Adapta a Frente 4 sem confundir seu dataset de 7 kW com outros equipamentos."""
from decimal import Decimal
from fastapi import HTTPException
from condocharge_ai.anomaly import check_session
from backend.api.schemas import SessionIn, DetectionOut
from backend.db.models import Charger

STATUS_TO_AI = {"completed": "completed", "user_stopped": "stopped_by_user",
                "system_failure": "interrupted_by_failure", "abnormal_disconnection": "abnormal_disconnection"}


def flagged(code: str, message: str, layer="rules") -> DetectionOut:
    return DetectionOut(is_anomaly=True, layer=layer, score=1.0 if layer == "rules" else None,
                        reasons=[code], reasons_human=[message], model_version=None)


def detect(dto: SessionIn, charger: Charger) -> DetectionOut:
    # O mesmo limite de balanço aceito pelo rateio; não aprovar o que ele não conseguirá faturar.
    if abs(dto.green_kwh + dto.grid_kwh - dto.total_kwh) > Decimal("0.05"):
        return flagged("ENERGY_SOURCE_ATTRIBUTION_MISMATCH", "Green + Grid diverge do total medido.")
    duration = Decimal(str((dto.ended_at - dto.started_at).total_seconds() / 3600))
    if dto.max_power_kw > charger.rated_power_kw * Decimal("1.05"):
        return flagged("POWER_EXCEEDS_NOMINAL", "Potência acima da capacidade cadastrada.")
    if dto.total_kwh > charger.rated_power_kw * duration * Decimal("1.05") + Decimal("0.05"):
        return flagged("KWH_EXCEEDS_CAPACITY", "Energia impossível para a duração e capacidade cadastradas.")
    if dto.average_power_kw > dto.max_power_kw:
        return flagged("AVERAGE_EXCEEDS_MAX_POWER", "Potência média maior que a máxima.")
    if charger.code != "HCA01" or charger.rated_power_kw != Decimal("7"):
        return flagged("ML_OUT_OF_SCOPE", "Modelo treinado no HCA01 de 7 kW; requer revisão para outro regime.",
                       "scope")
    data = {name: float(getattr(dto, name)) for name in
            ("total_kwh", "green_kwh", "grid_kwh", "average_power_kw", "max_power_kw")}
    data.update(session_id=dto.session_id, charger_id=charger.code, card_id=dto.card_id or "shared",
                started_at=dto.started_at, ended_at=dto.ended_at, status=STATUS_TO_AI[dto.status])
    try:
        result = DetectionOut.model_validate(check_session(data))
    except (FileNotFoundError, ValueError, ImportError, OSError) as exc:
        raise HTTPException(503, "Modelo de IA indisponível; execute o bootstrap do projeto") from exc
    if dto.status == "abnormal_disconnection":
        # Motivo ambíguo não equivale automaticamente a falha nem a parada voluntária.
        result.is_anomaly = True
        result.reasons.append("AMBIGUOUS_END_STATUS")
        result.reasons_human.append("Desconexão anormal: confirmar o motivo antes de faturar.")
        if result.layer == "passed":
            result.layer = "rules"
    return result
