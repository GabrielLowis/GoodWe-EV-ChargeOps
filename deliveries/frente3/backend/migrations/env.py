## Ambiente do Alembic. ##

"""A URL do banco vem, nesta ordem:
  1. da opção sqlalchemy.url definida programaticamente (usado pelos testes);
  2. da variável de ambiente DATABASE_URL (backend/config.py). """

# fileConfig lê a configuração das mensagens de log, que fica no alembic.ini.
from logging.config import fileConfig

# context: tudo o que o Alembic sabe sobre a execução atual (qual comando, qual configuração, qual banco).
from alembic import context
# engine_from_config cria a conexão com o banco a partir da configuração.
# pool reúne as formas de guardar conexões para reaproveitar (aqui usamos o NullPool,
from sqlalchemy import engine_from_config, pool

# Nossas configurações (backend/config.py). O "as app_config" dá outro nome ao import, para não confundir
# com a variável "config" do Alembic, criada logo abaixo.
from backend import config as app_config
# Importar o models.py cria as classes (tabelas) e registra todas no Base.metadata.
from backend.db import models  # noqa: F401  (registra as tabelas no metadata)
from backend.db.base import Base

# As opções do alembic.ini (ou as que os testes e a demo definem direto no código).
config = context.config

# Liga as mensagens de log definidas no alembic.ini. Os testes e a demo desligam isso para não bagunçar a saída deles.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

# Endereço do banco. O alembic.ini, de propósito, não guarda endereço nem senha: se ninguém informou, 
# usa o DATABASE_URL do config.py. Os testes informam o endereço do banco de testes antes de chegar aqui.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)

# O "catálogo" das tabelas dos modelos. Serve para o Alembic comparar os modelos com o banco (por exemplo, no "alembic revision --autogenerate").
target_metadata = Base.metadata

# Modo offline: em vez de executar, só escreve o SQL que seria executado, sem conectar ao banco.
def run_migrations_offline() -> None:
    """Gera o SQL sem conectar ao banco (alembic upgrade head --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# Modo online (o normal): conecta ao banco e executa as migrations de verdade.
def run_migrations_online() -> None:
    # Quem chama o Alembic pode entregar uma conexão já aberta. No projeto, hoje ninguém faz isso,
    connectable = config.attributes.get("connection")
    if connectable is None:
        # Cria a conexão a partir das opções que começam com "sqlalchemy." (ou seja, a sqlalchemy.url).
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        # O "with" fecha a conexão sozinho no fim do bloco, mesmo se der erro.
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            # Tudo roda numa transação: se uma migration falhar no meio, nada fica pela metade.
            with context.begin_transaction():
                context.run_migrations()
    else:
        # Usa a conexão que já veio pronta.
        context.configure(connection=connectable, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

# Escolhe o modo: offline quando o comando tem --sql; online em todos os outros casos.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
