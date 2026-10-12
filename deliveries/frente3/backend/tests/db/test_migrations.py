### Checklist da Sprint 2: 'PostgreSQL e migrations funcionam do zero'. ###

# Estes testes pedem direto o db_engine (o engine que abre as conexões, criado uma vez por rodada), e
# não a sessão isolada "db": eles olham a ESTRUTURA do banco (quais tabelas existem e como são), e não os dados.

import pytest
from alembic import command

# compare_metadata faz a mesma comparação do "alembic revision --autogenerate": aponta as diferenças
# entre os modelos Python (models.py) e as tabelas que existem de verdade no banco.
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

# inspect permite perguntar ao banco como ele está montado (ex.: o nome de cada tabela).
from sqlalchemy import inspect

from backend import config as app_config

# Importar models faz cada classe de tabela se registrar em Base.metadata (o "catálogo" de tabelas do
# ORM). O nome models não é usado depois, e o aviso noqa (código F401) pede ao ruff que não reclame disso.
from backend.db import models  # noqa: F401  (registra as tabelas)
from backend.db.base import Base
from backend.tests.conftest import alembic_config

# pytestmark marca TODOS os testes deste arquivo com a marca "db" (precisam do PostgreSQL).
pytestmark = pytest.mark.db

# As 16 tabelas que o banco precisa ter depois da migration. Chaves { } com valores soltos (sem o
# formato "nome": valor de um dicionário) formam um conjunto (set): uma coleção sem ordem e sem repetição.
EXPECTED_TABLES = {
    # 10 entidades do plano da Sprint 2
    "users",
    "condo_units",
    "chargers",
    "reservations",
    "charging_sessions",
    "tariffs",
    "invoices",
    "invoice_items",
    "anomalies",
    "audit_events",
    # tabelas de apoio
    "rfid_cards",
    "session_power_samples",
    "tariff_bands",
    "tariff_windows",
    "tax_rules",
    "holidays",
}


# O banco tem exatamente essas 16 tabelas: nenhuma faltando e nenhuma sobrando. A alembic_version sai da
# conta porque é a tabelinha onde o Alembic anota qual versão da migration está aplicada.
# Entre conjuntos, "-" tira elementos e "==" compara sem se importar com a ordem.
def test_todas_as_tabelas_existem(db_engine):
    tables = set(inspect(db_engine).get_table_names()) - {"alembic_version"}
    assert tables == EXPECTED_TABLES


# Os modelos do ORM e a migration descrevem o mesmo banco? compare_metadata devolve a lista de diferenças
# (tabela, coluna, tipo...), e lista vazia quer dizer nenhuma diferença. compare_type=True também compara
# o tipo de cada coluna. Se alguém mudar models.py e esquecer a migration (ou o contrário), este teste avisa.
def test_modelos_orm_e_migration_nao_divergem(db_engine):
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []


# A migration funciona nos dois sentidos: downgrade até "base" apaga tudo (sobra no máximo a
# alembic_version; "<=" entre conjuntos quer dizer "está contido em") e upgrade até "head" recria as
# 16 tabelas. No fim o banco volta completo, porque os testes seguintes precisam das tabelas.
def test_downgrade_e_upgrade_do_zero(db_engine):
    cfg = alembic_config(app_config.TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    assert set(inspect(db_engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(cfg, "head")
    assert set(inspect(db_engine).get_table_names()) - {"alembic_version"} == EXPECTED_TABLES

