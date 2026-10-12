import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, reservations, sessions, anomalies, billing, recommendation

app = FastAPI(
    title="EV ChargeOps",
    description="Back-end do rateio de recargas de veiculos eletricos em infraestrutura compartilhada.",
)

# Origem do front (Vite roda em 5173). Configuravel por variavel de ambiente.
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.get("/saude")
def saude():
    return {"status": "ok"}


for module in (auth, reservations, sessions, anomalies, billing, recommendation):
    app.include_router(module.router)
