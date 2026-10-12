import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ai.recommendation import recommend_window
from database import get_db
from models import User
from security import get_current_user
from services.billing import active_bands

router = APIRouter(tags=["Recomendacao"])


@router.get("/recomendacao-janela")
def recommend(kwh: float = Query(gt=0, le=200), power_kw: float = Query(default=7.0, gt=0, le=22),
              db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Melhor horario (proximas 24h) para carregar `kwh` e comparacao com carregar agora."""
    now = datetime.datetime.now()
    bands = active_bands(db, now.date())
    if not bands:
        raise HTTPException(422, "Nenhuma faixa tarifaria vigente configurada")
    try:
        return recommend_window(now, kwh, power_kw, bands)
    except ValueError as e:
        raise HTTPException(422, str(e))
