import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from backend.api.security import secret
from backend.api.routes import router
from backend.faturamento.service import InvoiceClosedError, ReviewError
from backend.rateio.models import InvalidTariffError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    secret()
    yield


app = FastAPI(title="EV ChargeOps", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=[s.strip() for s in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
app.include_router(router, prefix="/api")


@app.exception_handler(IntegrityError)
async def conflict(_: Request, exc: IntegrityError):
    logger.warning("Conflito de integridade: %s", getattr(exc.orig, "sqlstate", "unknown"))
    return JSONResponse(status_code=409, content={"detail": "Conflito de dados: duplicidade, sobreposição ou registro protegido"})


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError):
    logger.error("Banco indisponível: %s", type(exc.orig).__name__)
    return JSONResponse(status_code=503, content={"detail": "Banco de dados indisponível"})


@app.exception_handler(InvoiceClosedError)
@app.exception_handler(ReviewError)
async def domain_conflict(_: Request, exc: Exception):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidTariffError)
async def invalid_tariff(_: Request, exc: InvalidTariffError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
