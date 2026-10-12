## Funções auxiliares dos testes (tarifa de demonstração e sessões de exemplo).##

# Atalhos usados por vários testes. A ideia é cada teste escrever só o que importa para ele:
# make_session(ended_at=at(21, 12, 16)) em vez de montar uma sessão inteira com 11 campos.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from backend import config as app_config
from backend.db.enums import Band, SessionEndStatus, ValidationStatus
from backend.rateio.models import BandPrice, SessionInput, TariffSpec, TimeWindow
from backend.seeds.demo import DEMO_WINDOWS, TARIFF_V2_PRICES

# Fuso do condomínio (America/Sao_Paulo), usado em todas as datas dos testes.
TZ = app_config.CONDO_TIMEZONE


# Monta a tabela tarifária de demonstração (a mesma versão 2 do seed) no formato do motor.
# Todos os parâmetros têm valor padrão, então o teste só passa o que quer mudar.
# Ex.: build_tariff(overhead="0") é a mesma tabela, sem overhead.
def build_tariff(
    prices: dict[Band, tuple[Decimal, Decimal]] = TARIFF_V2_PRICES,
    idle_fee: str = "0.25",
    overhead: str = "5.00",
    weekends_holidays_off_peak: bool = True,
    tariff_id: int | None = 2,
) -> TariffSpec:
    """Tabela tarifária de demonstração (versão 2 do seed)."""
    return TariffSpec(
        id=tariff_id,
        name="Tabela de teste",
        # Cada faixa tem um par (Green, Grid); "for band, (green, grid) in ..." separa a faixa e os dois
        # preços, que viram um BandPrice.
        prices={band: BandPrice(green, grid) for band, (green, grid) in prices.items()},
        # As 3 janelas de dia útil: intermediário 17h-18h, ponta 18h-21h e intermediário 21h-22h.
        windows=tuple(TimeWindow(b, s, e) for b, s, e in DEMO_WINDOWS),
        idle_tolerance_minutes=15,
        idle_fee_per_minute=Decimal(idle_fee),
        overhead_percent=Decimal(overhead),
        weekends_holidays_off_peak=weekends_holidays_off_peak,
    )


# Atalho para datas: at(21, 17, 30) = 21/09/2026 às 17:30, já no fuso do condomínio.
# Mês e segundos são opcionais: at(1, 0, month=10) = 01/10/2026 à meia-noite.
def at(day: int, hour: int, minute: int = 0, month: int = 9, second: int = 0) -> datetime:
    """Horário local do condomínio em 2026 (setembro por padrão)."""
    return datetime(2026, month, day, hour, minute, second, tzinfo=TZ)


# Uma sessão "comum" pronta, que cada teste ajusta. Das 10h às 12h de uma segunda-feira é tudo fora de
# ponta, então, sem ajustes, ela custa 14 kWh x R$ 0,65 = R$ 9,10 de energia.
# - **overrides recebe qualquer campo pelo nome: make_session(user_id=None) troca só o morador.
# - data.update(overrides) põe os valores do teste por cima dos padrões; o resto fica igual.
# - SessionInput(**data) "espalha" o dicionário como parâmetros nomeados (session_id=1, user_id=10...).
def make_session(**overrides) -> SessionInput:
    """Sessão concluída e aprovada, 21/09/2026 (segunda-feira) das 10h às 12h, 14 kWh da rede."""
    data = dict(
        session_id=1,
        user_id=10,
        started_at=at(21, 10),
        energy_ended_at=at(21, 12),
        ended_at=at(21, 12),
        total_kwh=Decimal("14.000"),
        green_kwh=Decimal("0.000"),
        grid_kwh=Decimal("14.000"),
        end_status=SessionEndStatus.COMPLETED,
        validation_status=ValidationStatus.APPROVED,
        charger_rated_power_kw=Decimal("7.00"),
    )
    data.update(overrides)
    return SessionInput(**data)
