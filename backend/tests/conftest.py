"""Fixtures compartilhadas.

- Testes do motor (tests/rateio) não precisam de banco.
- Testes marcados com `db` usam o PostgreSQL de TEST_DATABASE_URL. Se o banco
  não estiver acessível, eles são pulados com aviso (os do motor continuam).
  Cada teste roda dentro de uma transação desfeita no final (rollback).
"""


# Como ler este arquivo:
# - conftest.py é um nome especial: o pytest carrega este arquivo sozinho, antes dos testes, e tudo o que
#   está aqui fica disponível para os testes desta pasta e das subpastas, sem precisar de import.
# - Uma "fixture" (@pytest.fixture) é uma preparação reutilizável. O teste pede a fixture pelo NOME, como
#   parâmetro: "def test_x(tariff):" faz o pytest rodar a função tariff() abaixo e entregar o resultado
#   ao teste. Assim cada teste recebe a sua tarifa pronta, sem repetir o código de montagem.
# - Fixture com "yield" tem duas metades: o que vem antes do yield prepara, o valor do yield vai para o
#   teste, e o que vem depois roda quando o teste termina (a limpeza).

from __future__ import annotations

# Iterator: o tipo de uma função com yield (usado só nas anotações de tipo).
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest

# command: as mesmas ações do terminal (alembic upgrade, alembic downgrade), chamadas de dentro do Python.
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

# OperationalError: o erro que o SQLAlchemy lança quando não consegue falar com o banco (ex.: desligado).
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend import config as app_config
from backend.rateio.models import TariffSpec, TaxRuleSpec
from backend.tests.helpers import build_tariff

# Raiz do projeto. Este arquivo está em backend/tests/conftest.py: parents[0] é backend/tests,
# parents[1] é backend e parents[2] é a raiz (onde fica o alembic.ini).
ROOT = Path(__file__).resolve().parents[2]


# Função "gancho" (hook): o pytest a chama sozinho ao iniciar. Ela registra a marca "db", usada nos
# arquivos de teste do banco (pytestmark = pytest.mark.db); sem o registro, o pytest avisaria que não
# conhece essa marca. A marca também permite escolher o que rodar:
#   python -m pytest backend/tests -m db          -> só os testes do banco
#   python -m pytest backend/tests -m "not db"    -> só os testes do motor
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: teste de integração que precisa do PostgreSQL")


# ---------------------------------------------------------------------------
# Motor (sem banco)
# ---------------------------------------------------------------------------
# A tabela tarifária de demonstração (versão 2 do seed): o kWh da rede custa R$ 0,65 fora de ponta,
# R$ 0,95 no intermediário e R$ 1,45 na ponta; o kWh solar custa R$ 0,30 em qualquer faixa; a ociosidade
# custa R$ 0,25 por minuto e o overhead é de 5%. Cada teste que pede "tariff" recebe uma tarifa nova.
@pytest.fixture
def tariff() -> TariffSpec:
    return build_tariff()


# Uma lista com um imposto só: ISS de 5% (alíquota demonstrativa, a mesma do seed).
@pytest.fixture
def iss_5() -> list[TaxRuleSpec]:
    return [TaxRuleSpec(tax_type="iss", rate_percent=Decimal("5"), id=1)]


# ---------------------------------------------------------------------------
# Banco de dados (PostgreSQL)
# ---------------------------------------------------------------------------
# Configuração do Alembic para o banco de TESTE. O set_main_option informa o endereço, e o env.py usa
# esse endereço no lugar do DATABASE_URL (o banco de trabalho). configure_logger = False pede ao env.py
# que não mexa nos logs, para não bagunçar a saída do pytest.
def alembic_config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    return cfg


# O engine do banco de teste: o objeto do SQLAlchemy que abre as conexões (uma "fábrica" de conexões).
# scope="session" faz esta fixture rodar UMA vez para a rodada inteira de testes (e não uma vez por
# teste), porque montar o banco é a parte demorada. Passo a passo:
#   1. Um "SELECT 1" (a consulta mais simples que existe) só para ver se o banco responde.
#   2. Se não responder, pytest.skip pula todos os testes que dependem desta fixture e mostra o motivo.
#      exc.orig é o erro original do driver (psycopg). O comentário "pragma: no cover" pede às
#      ferramentas de cobertura de testes que ignorem esse trecho, que só roda com o banco desligado.
#   3. downgrade até "base" apaga todas as tabelas e upgrade até "head" recria tudo pela migration: cada
#      rodada começa com um banco limpo, montado pela mesma migration que cria o banco de verdade.
#   4. yield entrega o engine aos testes; depois do último teste, dispose() fecha as conexões.
@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    if not make_url(app_config.TEST_DATABASE_URL).database.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL deve apontar para banco exclusivo com sufixo _test")
    engine = create_engine(app_config.TEST_DATABASE_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:  # pragma: no cover - depende do ambiente
        pytest.fail("PostgreSQL de teste indisponível; inicie o banco exclusivo antes de testar")
    cfg = alembic_config(app_config.TEST_DATABASE_URL)
    command.downgrade(cfg, "base")  # garante banco limpo, criado do zero pela migration
    command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


# A sessão de banco que cada teste recebe ao pedir "db". Repare que esta fixture pede outra (db_engine)
# do mesmo jeito que um teste pede: fixtures podem depender umas das outras. O truque do isolamento:
#   1. Abre uma conexão e começa uma transação "de fora" (begin).
#   2. Cria a Session do SQLAlchemy presa a essa transação. Com join_transaction_mode="create_savepoint",
#      um commit feito pelo código testado vira só um ponto de salvamento (savepoint) dentro da transação
#      de fora: nada é gravado de forma definitiva. expire_on_commit=False mantém os objetos legíveis
#      depois de um commit, sem reler do banco.
#   3. yield entrega a sessão ao teste, que grava, consulta e confere à vontade.
#   4. O finally roda sempre, mesmo se o teste falhar: fecha a sessão e o rollback desfaz TUDO o que o
#      teste gravou.
# Resultado: todo teste começa com as tabelas vazias, e um teste nunca atrapalha o outro.
@pytest.fixture
def db(db_engine: Engine) -> Iterator[Session]:
    """Sessão isolada: tudo que o teste gravar é desfeito no final."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
