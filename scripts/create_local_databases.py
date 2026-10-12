"""Cria só os dois bancos nomeados na configuração, sem apagar nenhum banco."""
import os
from dotenv import load_dotenv
import psycopg
from psycopg import sql

load_dotenv()
with psycopg.connect(host="127.0.0.1", port=5432, user=os.environ["POSTGRES_USER"],
                    password=os.environ["POSTGRES_PASSWORD"], dbname="postgres", autocommit=True) as db:
    for name in [os.environ.get("POSTGRES_DB", "evchargeops"), "evchargeops_test"]:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            print(f"Banco {name} criado.")
