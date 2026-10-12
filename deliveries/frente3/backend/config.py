"""Configuração da Frente 3, lida de variáveis de ambiente (ver .env.example).

Nada de credencial fica no código: os valores padrão abaixo servem apenas para
o PostgreSQL local do docker-compose de desenvolvimento.
"""

import os
from zoneinfo import ZoneInfo

# Banco principal (desenvolvimento/demo) e banco exclusivo dos testes de integração.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/evchargeops",
)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/evchargeops_test",
)

# Fuso horário do condomínio.
CONDO_TIMEZONE = ZoneInfo(os.getenv("CONDO_TIMEZONE", "America/Sao_Paulo"))

# Jurisdição tributária do condomínio (município/estado). 
TAX_JURISDICTION = os.getenv("TAX_JURISDICTION", "BR-SP-SAO_PAULO")
