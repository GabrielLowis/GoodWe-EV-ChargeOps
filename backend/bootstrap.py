"""Bootstrap explícito e idempotente de desenvolvimento. Nunca faz seed sem a flag."""
import os
from datetime import datetime, UTC, time
from decimal import Decimal
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from backend.api.database import SessionLocal
from backend.api.security import hash_password, secret
from backend.db.models import User, CondoUnit, Charger, Tariff, TariffBand, TariffWindow, TaxRule
from condocharge_ai import ml_model
from condocharge_ai.training.train import main as train


def seed(db):
    if os.getenv("SEED_DEMO", "false").lower() != "true":
        return
    password = os.environ["DEMO_PASSWORD"]
    if db.scalar(select(User.id).limit(1)):
        return  # Não substitui usuários, senhas, tarifas ou dados existentes.
    unit = CondoUnit(block="A", number="101")
    db.add(unit)
    db.flush()
    db.add_all([
        User(name="Síndico Demo", email="sindico@demo.local", role="manager", password_hash=hash_password(password)),
        User(name="Morador Demo", email="morador@demo.local", role="resident", unit_id=unit.id,
             password_hash=hash_password(password)),
        Charger(code="HCA01", serial_number="DEMO-HCA01", model="GoodWe HCA G2",
                rated_power_kw=Decimal("7"), connectors=1, location="Vaga compartilhada (simulação)")])
    valid = datetime(2026, 1, 1, tzinfo=UTC)
    tariff = Tariff(name="Demonstração acadêmica", valid_from=valid, idle_fee_per_minute=Decimal("0.25"),
                    overhead_percent=Decimal("5"), weekends_holidays_off_peak=True)
    tariff.bands = [TariffBand(band=b, green_price_per_kwh=Decimal("0.30"), grid_price_per_kwh=Decimal(p))
                    for b, p in [("off_peak", "0.65"), ("intermediate", "0.95"), ("peak", "1.45")]]
    tariff.windows = [TariffWindow(band=b, start_time=time(start), end_time=time(end))
                      for b, start, end in [("intermediate", 17, 18), ("peak", 18, 21), ("intermediate", 21, 22)]]
    db.add_all([tariff, TaxRule(tax_type="iss", jurisdiction="BR-SP-SAO_PAULO", rate_percent=Decimal("5"),
                              valid_from=valid, legal_basis="Parâmetro fictício de demonstração acadêmica")])
    db.commit()


def main():
    secret()
    command.upgrade(Config("alembic.ini"), "head")
    # Reconstroi no runtime escolhido, sem desserializar o pickle recebido como anexo.
    if not ml_model.CAMINHO_MODELO.is_file():
        ml_model.CAMINHO_MODELO.parent.mkdir(parents=True, exist_ok=True)
        train()
    ml_model.carregar_modelo()
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    main()
