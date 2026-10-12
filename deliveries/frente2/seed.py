"""Dados de demonstracao: unidade, carregador, gestor, morador, faixas tarifarias e parametros.

Uso:  python seed.py     (idempotente: pode rodar mais de uma vez)
Os valores de tarifa sao DE EXEMPLO, apenas para demonstrar o motor de rateio.
"""
import datetime
import os
from decimal import Decimal
from sqlalchemy import select

from models import (CondoUnit, Charger, User, ProfileUser, Tariff, BillingConfig)
from security import hash_password


def seed(db):
    unit = db.scalar(select(CondoUnit).where(CondoUnit.unit == "Bloco A - 101"))
    if unit is None:
        unit = CondoUnit(unit="Bloco A - 101")
        db.add(unit)
    if db.get(Charger, "HCA01") is None:
        db.add(Charger(id="HCA01"))
    db.flush()

    manager_pw = os.getenv("SEED_MANAGER_PASSWORD", "gestor-demo-123")
    resident_pw = os.getenv("SEED_RESIDENT_PASSWORD", "morador-demo-123")
    if db.scalar(select(User).where(User.email == "sindico@demo.com")) is None:
        db.add(User(name="Sindico Demo", email="sindico@demo.com", unit_id=unit.id,
                    profile=ProfileUser.Gestor, password_hash=hash_password(manager_pw)))
    if db.scalar(select(User).where(User.email == "morador@demo.com")) is None:
        db.add(User(name="Morador Demo", email="morador@demo.com", unit_id=unit.id,
                    profile=ProfileUser.Morador, password_hash=hash_password(resident_pw)))

    start = datetime.date(2026, 1, 1)
    if db.scalar(select(Tariff)) is None:
        T = datetime.time
        for name, a, b, g, r in [
            ("Fora de ponta", T(21, 0), T(17, 30), "0.35", "0.60"),
            ("Intermediaria", T(17, 30), T(18, 0), "0.45", "0.80"),
            ("Ponta", T(18, 0), T(21, 0), "0.55", "1.10"),
        ]:
            db.add(Tariff(name=name, start_time=a, end_time=b, green_price=Decimal(g),
                          grid_price=Decimal(r), valid_from=start))
    if db.scalar(select(BillingConfig)) is None:
        db.add(BillingConfig(idle_fee_per_min=Decimal("0.50"), idle_tolerance_min=15,
                             tax_pct=Decimal("5.00"), overhead_pct=Decimal("10.00"), valid_from=start))
    db.commit()


if __name__ == "__main__":
    from database import SessionLocal
    with SessionLocal() as db:
        seed(db)
    print("Seed concluido: gestor sindico@demo.com e morador morador@demo.com (senhas no seed.py / .env).")
