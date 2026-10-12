#Base declarativa do SQLAlchemy e cria as conexão.

# Seria o motor que guarda o endereco do banco e cuida das conexoes 
from sqlalchemy import Engine, create_engine
#DeclarativeBase: base do SQLAlchemy que transforma classes Python em tabelas. e o sessionmaker fabrica essas sessoes
from sqlalchemy.orm import DeclarativeBase, sessionmaker
# Configurações do projeto (backend/config.py), como o endereço do banco 
from backend import config

#Classe-mãe de todos os modelos ORM do EV ChargeOps
class Base(DeclarativeBase):
    pass

#Cria o engine do SQLAlchemy. Sem argumento, usa DATABASE_URL
def make_engine(url: str | None = None, **kwargs) -> Engine:
    return create_engine(url or config.DATABASE_URL, **kwargs)

#fabrica de sessões. expire_on_commit=False evita recarregar objetos após o commit.
def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
