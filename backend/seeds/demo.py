"""Dados de demonstração da Frente 3 (setembro/2026).

Todos os nomes, e-mails, preços e alíquotas são FICTÍCIOS e servem apenas
para demonstrar o motor. Os preços reais são definidos pela assembleia e a
alíquota real depende do enquadramento tributário (ver Frente 2).

Cada sessão foi escolhida para exercitar uma regra da Sprint 1:

  S0  Diego  28/08 21:30  lançamento posterior: anomalia aprovada em setembro, tarifa antiga
  S1  Ana    07/09 18:30  feriado (Independência): fora de ponta o dia todo
  S2  Ana    09/09 10:00  ociosidade de 14 min: dentro da tolerância, R$ 0
  S3  Diego  10/09 08:00  ociosidade de 16 min: 1 min cobrado (fim da carga pela curva)
  S4  Bruno  11/09 21:30  encerrada pelo morador: só energia, sem ociosidade
  S5  Diego  14/09 19:00  falha do sistema: registrada, R$ 0
  S6  Diego  15/09 20:00  50 kWh em 90 min num carregador de 7 kW: anomalia rejeitada
  S7  (sem)  19/09 10:00  sessão sem reserva correspondente: não faturada
  S8  Ana    21/09 17:30  exemplo do plano: atravessa intermediário -> ponta (curva de potência)
  S9  Bruno  22/09 19:00  exatamente o SessionDTO de exemplo do plano (sem fim de energia)
  Carla não carregou no mês (tem um no-show): fatura zero.
  Ana e Bruno moram na mesma unidade (A-101): duas faturas separadas.
"""
# Este arquivo monta um condomínio de mentira dentro do banco: tarifas, imposto, feriados, moradores,
# um carregador, reservas, 10 recargas e 2 anomalias. É o cenário usado pela demo (scripts/demo_frente3.py)
# e pelos testes de faturamento. As recargas são gravadas direto no banco; elas não vêm do simulador da Frente 1.

from __future__ import annotations

# field(default_factory=...) cria um valor novo (ex.: um dicionário vazio) para cada objeto.
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend import config
from backend.db.enums import (
    AnomalyStatus,
    AttributionMethod,
    Band,
    DataSource,
    ReservationStatus,
    SessionEndStatus,
    UserRole,
    ValidationStatus,
)
from backend.db.models import (
    Anomaly,
    Charger,
    ChargingSession,
    CondoUnit,
    Holiday,
    Reservation,
    RfidCard,
    SessionPowerSample,
    Tariff,
    TariffBand,
    TariffWindow,
    TaxRule,
    User,
)
from backend.seeds.holidays import aneel_national_holidays

TZ: ZoneInfo = config.CONDO_TIMEZONE  # fuso do condomínio (America/Sao_Paulo)
D = Decimal  # apelido curto: D("0.30") é o mesmo que Decimal("0.30")

# Janelas de dia útil espelhando a Tarifa Branca (Frente 1): ponta 18h-21h e
# intermediário na hora anterior e na posterior. O resto do dia é fora de ponta.
DEMO_WINDOWS = (
    (Band.INTERMEDIATE, time(17, 0), time(18, 0)),
    (Band.PEAK, time(18, 0), time(21, 0)),
    (Band.INTERMEDIATE, time(21, 0), time(22, 0)),
)

# Preços por kWh (Green, Grid) de cada versão da tabela - valores fictícios.
# A versão 1 vale até 31/08 e a versão 2 a partir de 01/09: é isso que mostra a tarifa versionada.
TARIFF_V1_PRICES = {
    Band.OFF_PEAK: (D("0.25"), D("0.60")),
    Band.INTERMEDIATE: (D("0.25"), D("0.90")),
    Band.PEAK: (D("0.25"), D("1.40")),
}
TARIFF_V2_PRICES = {
    Band.OFF_PEAK: (D("0.30"), D("0.65")),
    Band.INTERMEDIATE: (D("0.30"), D("0.95")),
    Band.PEAK: (D("0.30"), D("1.45")),
}


# Atalho para criar um horário já no fuso do condomínio: local(2026, 9, 21, 17, 30) = 21/09/2026 17:30.
def local(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=TZ)


# Guarda os ids que o banco gerou (ex.: ids.users["ana"]), para a demo e os testes acharem cada registro.
@dataclass
class DemoIds:
    """IDs gerados pelo banco, para o script de demo e os testes."""

    # default_factory=dict: cada DemoIds ganha um dicionário vazio próprio. O Python não aceita "= {}"
    # aqui, porque todos os objetos acabariam dividindo o mesmo dicionário.
    users: dict[str, int] = field(default_factory=dict)
    sessions: dict[str, int] = field(default_factory=dict)
    anomalies: dict[str, int] = field(default_factory=dict)
    tariffs: dict[str, int] = field(default_factory=dict)
    tax_rules: dict[str, int] = field(default_factory=dict)
    charger_id: int = 0


# Monta uma versão da tabela tarifária com os preços das 3 faixas e as 3 janelas de dia útil.
def _tariff(
    name: str, valid_from: datetime, valid_to: datetime | None, prices, idle_fee: str, overhead: str, reference: str
) -> Tariff:
    tariff = Tariff(
        name=name,
        valid_from=valid_from,
        valid_to=valid_to,
        idle_tolerance_minutes=15,
        idle_fee_per_minute=D(idle_fee),
        overhead_percent=D(overhead),
        weekends_holidays_off_peak=True,
        assembly_reference=reference,
    )
    # Uma linha de preço para cada faixa: "for b, (g, r) in prices.items()" separa a faixa e os dois preços.
    tariff.bands = [TariffBand(band=b, green_price_per_kwh=g, grid_price_per_kwh=r) for b, (g, r) in prices.items()]
    tariff.windows = [TariffWindow(band=b, start_time=s, end_time=e) for b, s, e in DEMO_WINDOWS]
    return tariff


# Monta uma curva de potência: uma medição a cada 5 minutos, com as potências da lista (em kW).
def _curve(start: datetime, points: list[str], step_minutes: int = 5) -> list[SessionPowerSample]:
    return [
        SessionPowerSample(measured_at=start + timedelta(minutes=i * step_minutes), power_kw=D(p))
        for i, p in enumerate(points)
    ]


# Função principal: cria o cenário inteiro. Não faz commit (quem chama decide).
def seed_demo(db: Session) -> DemoIds:
    """Popula um banco vazio com o cenário de demonstração. Não faz commit."""
    ids = DemoIds()

    #  Parâmetros: tarifas versionadas, imposto e feriados 
    t1 = _tariff(
        "Tabela tarifária 2026 - versão 1",
        local(2026, 1, 1, 0),
        local(2026, 9, 1, 0),
        TARIFF_V1_PRICES,
        "0.20",
        "3.00",
        "Ata da AGO de 15/12/2025 (fictícia)",
    )
    t2 = _tariff(
        "Tabela tarifária 2026 - versão 2",
        local(2026, 9, 1, 0),
        None,  # sem data de término: vale "até segunda ordem"
        TARIFF_V2_PRICES,
        "0.25",
        "5.00",
        "Ata da AGE de 10/08/2026 (fictícia)",
    )
    # Imposto demonstrativo de 5% (a alíquota real depende da análise tributária da Frente 2).
    iss = TaxRule(
        tax_type="iss",
        jurisdiction=config.TAX_JURISDICTION,
        rate_percent=D("5.000"),
        exclude_compensated_energy=False,
        legal_basis="LC 116/2003, item 14.01 (recarga como serviço) - alíquota DEMONSTRATIVA",
        valid_from=local(2026, 1, 1, 0),
    )
    # db.add / db.add_all colocam os objetos na fila para serem gravados.
    db.add_all([t1, t2, iss])
    db.add_all(Holiday(holiday_date=d, description=n) for d, n in aneel_national_holidays(2026).items())

    # Cadastros 
    a101 = CondoUnit(block="A", number="101")
    a102 = CondoUnit(block="A", number="102")
    b201 = CondoUnit(block="B", number="201")
    db.add_all([a101, a102, b201])
    manager = User(name="Helena Prado (síndica)", email="sindica@demo.evchargeops.dev", role=UserRole.MANAGER)
    ana = User(name="Ana Souza", email="ana@demo.evchargeops.dev", role=UserRole.RESIDENT, unit=a101)
    bruno = User(name="Bruno Lima", email="bruno@demo.evchargeops.dev", role=UserRole.RESIDENT, unit=a101)
    carla = User(name="Carla Mendes", email="carla@demo.evchargeops.dev", role=UserRole.RESIDENT, unit=a102)
    diego = User(name="Diego Rocha", email="diego@demo.evchargeops.dev", role=UserRole.RESIDENT, unit=b201)
    db.add_all([manager, ana, bruno, carla, diego])
    charger = Charger(
        code="HCA01",
        serial_number="SN-DEMO-HCA01",  # substituir pelo SN real informado pela Frente 1
        model="GW7K-HCA-20",
        rated_power_kw=D("7.00"),
        connectors=1,
        location="Garagem - vaga rotativa (demo)",
    )
    db.add(charger)
    # flush envia a fila ao banco agora (sem confirmar): os objetos ganham id, e os próximos podem usá-lo.
    db.flush()
    db.add_all(
        [
            RfidCard(card_uid="RFID-05", label="Cartão 05", custodian_user_id=manager.id),
            RfidCard(card_uid="RFID-06", label="Cartão 06", custodian_user_id=manager.id),
        ]
    )

    # Reservas e sessões 
    
    # As duas funções abaixo ficam DENTRO de seed_demo, por isso enxergam db, charger e ids.

    # Cria uma reserva do morador no carregador da demo (já concluída, se nada for dito).
    def reserve(user: User, start: datetime, end: datetime, status: str = ReservationStatus.COMPLETED) -> Reservation:
        reservation = Reservation(
            user_id=user.id, charger_id=charger.id, connector=1, starts_at=start, ends_at=end, status=status
        )
        db.add(reservation)
        db.flush()
        return reservation

    # Cria uma recarga. Quando há morador, cria também a reserva dele, de 10 minutos antes do início até
    # 10 minutos depois do fim, e atribui a recarga por essa reserva.
    def session(
        key: str,
        user: User | None,
        start: datetime,
        energy_end: datetime | None,
        end: datetime,
        total: str,
        green: str,
        grid: str,
        end_status: str = SessionEndStatus.COMPLETED,
        validation: str = ValidationStatus.APPROVED,
        source: str = DataSource.SIMULATOR,
        external_id: str | None = None,
        card: str = "RFID-05",
        failure: str | None = None,
        samples: list[SessionPowerSample] | None = None,
        avg: str | None = None,
        max_kw: str | None = None,
    ) -> ChargingSession:
        reservation = None
        if user is not None:
            reservation = reserve(user, start - timedelta(minutes=10), end + timedelta(minutes=10))
        s = ChargingSession(
            source=source,
            external_id=external_id or f"SIM-{key}",
            charger_id=charger.id,
            connector=1,
            card_id=card,
            reservation_id=reservation.id if reservation else None,
            user_id=user.id if user else None,
            attribution_method=AttributionMethod.RESERVATION if user else AttributionMethod.UNATTRIBUTED,
            started_at=start,
            energy_ended_at=energy_end,
            ended_at=end,
            total_kwh=D(total),
            green_kwh=D(green),
            grid_kwh=D(grid),
            average_power_kw=D(avg) if avg else None,
            max_power_kw=D(max_kw) if max_kw else None,
            end_status=end_status,
            failure_code=failure,
            validation_status=validation,
        )
        s.samples = samples or []  # "samples or []": sem curva, usa uma lista vazia
        db.add(s)
        db.flush()
        ids.sessions[key] = s.id  # guarda o id com o apelido (S0, S1...)
        return s

    # Cada chamada abaixo segue a ordem: apelido, morador, início, fim da energia, desconexão,
    # kWh total, kWh Green, kWh Grid e, depois, os ajustes de cada caso.

    # S0: sessão de agosto que entra pendente. A anomalia a0 (mais abaixo) a suspende e a síndica aprova
    # depois: vira lançamento posterior na fatura de setembro, com a tarifa de agosto.
    s0 = session(
        "S0",
        diego,
        local(2026, 8, 28, 21, 30),
        local(2026, 8, 29, 0, 30),
        local(2026, 8, 29, 0, 40),
        "19.500",
        "0.000",
        "19.500",
        validation=ValidationStatus.PENDING,
    )
    # S1: 07/09 é feriado, então a sessão das 18:30 (que seria ponta) é toda fora de ponta.
    session(
        "S1",
        ana,
        local(2026, 9, 7, 18, 30),
        local(2026, 9, 7, 20, 0),
        local(2026, 9, 7, 20, 10),
        "9.000",
        "1.000",
        "8.000",
    )
    # S2: a energia para às 13:00 e o carro sai às 13:14 -> 14 minutos, dentro da tolerância (R$ 0).
    session(
        "S2",
        ana,
        local(2026, 9, 9, 10, 0),
        local(2026, 9, 9, 13, 0),
        local(2026, 9, 9, 13, 14),
        "18.000",
        "12.500",
        "5.500",
    )
    # S3: o fim da energia não é informado (None). O motor descobre pela curva: ~6,4 kW que caem até zero.
    s3_curve = _curve(local(2026, 9, 10, 8, 0), ["6.2"] + ["6.4"] * 27 + ["4.0", "1.5", "0.0", "0.0", "0.0", "0.0"])
    session(
        "S3",
        diego,
        local(2026, 9, 10, 8, 0),
        None,
        local(2026, 9, 10, 10, 46),
        "15.500",
        "6.000",
        "9.500",
        samples=s3_curve,
    )
    # S4: o morador encerrou antes do término: cobra só a energia, sem ociosidade.
    session(
        "S4",
        bruno,
        local(2026, 9, 11, 21, 30),
        local(2026, 9, 11, 22, 40),
        local(2026, 9, 11, 23, 30),
        "7.500",
        "0.000",
        "7.500",
        end_status=SessionEndStatus.USER_STOPPED,
    )
    # S5: falha do sistema: aparece na fatura com valor zero.
    session(
        "S5",
        diego,
        local(2026, 9, 14, 19, 0),
        local(2026, 9, 14, 19, 40),
        local(2026, 9, 14, 19, 40),
        "4.300",
        "0.000",
        "4.300",
        end_status=SessionEndStatus.SYSTEM_FAILURE,
        failure="SIM-COMM-LOSS (queda de comunicação simulada)",
    )
    # S6: 50 kWh em 1,5 h num carregador de 7 kW é fisicamente impossível. A anomalia a6 a suspende e a
    # síndica rejeita: não é cobrada.
    s6 = session(
        "S6",
        diego,
        local(2026, 9, 15, 20, 0),
        local(2026, 9, 15, 21, 30),
        local(2026, 9, 15, 21, 30),
        "50.000",
        "0.000",
        "50.000",
        validation=ValidationStatus.PENDING,
    )
    # S7: sem morador (None) e com outro cartão: fica sem atribuição e não entra em nenhuma fatura.
    session(
        "S7",
        None,
        local(2026, 9, 19, 10, 0),
        local(2026, 9, 19, 11, 0),
        local(2026, 9, 19, 11, 5),
        "6.500",
        "5.000",
        "1.500",
        card="RFID-06",
    )
    # S8: o exemplo do plano. Começa às 17:30 (intermediário) e vai até 20:30 (ponta); a curva de potência
    # decide quanto da energia fica em cada faixa.
    s8_curve = _curve(
        local(2026, 9, 21, 17, 30),
        ["6.6"] + ["6.9"] * 30 + ["6.0", "5.0", "4.0", "3.0", "2.0", "0.0", "0.0", "0.0", "0.0", "0.0"],
    )
    session(
        "S8",
        ana,
        local(2026, 9, 21, 17, 30),
        local(2026, 9, 21, 20, 30),
        local(2026, 9, 21, 20, 50),
        "19.200",
        "0.600",
        "18.600",
        samples=s8_curve,
    )
    # S9: os dados do SessionDTO de exemplo do plano, sem fim de energia e sem curva: a ociosidade não é
    # cobrada, porque não há como provar que o carro ficou parado depois da carga.
    session(
        "S9",
        bruno,
        local(2026, 9, 22, 19, 0),
        None,
        local(2026, 9, 22, 21, 10),
        "14.800",
        "4.200",
        "10.600",
        # Dados do SessionDTO de exemplo do plano, gravados como simulados: o grupo não tem
        # acesso à API SEMS+, então nenhuma sessão da demo é apresentada como vinda de lá.
        source=DataSource.SIMULATOR,
        external_id="abc123",
        avg="6.80",
        max_kw="7.10",
    )

    # Carla reservou e não apareceu: no-show não gera cobrança (consequência comportamental).
    reserve(carla, local(2026, 9, 17, 19, 0), local(2026, 9, 17, 21, 0), ReservationStatus.NO_SHOW)

    # Anomalias apontadas pela Frente 4 (entram como pendentes de revisão) 
    # Aqui o seed faz o papel da Frente 4: não existe modelo de IA neste pacote.
    a0 = Anomaly(
        session_id=s0.id,
        detector="isolation_forest",
        score=D("0.7100"),
        reasons=["duração acima do padrão do morador", "início em horário atípico"],
    )
    a6 = Anomaly(
        session_id=s6.id,
        detector="physical_rule",
        score=D("1.0000"),
        reasons=["50 kWh em 1,5 h excede o máximo físico de 7 kW x 1,5 h = 10,5 kWh"],
    )
    db.add_all([a0, a6])
    db.flush()  # o gatilho marca as duas sessões como 'suspended'

    # Anota os ids gerados para a demo e os testes.
    ids.users = {"manager": manager.id, "ana": ana.id, "bruno": bruno.id, "carla": carla.id, "diego": diego.id}
    ids.anomalies = {"S0": a0.id, "S6": a6.id}
    ids.tariffs = {"v1": t1.id, "v2": t2.id}
    ids.tax_rules = {"iss": iss.id}
    ids.charger_id = charger.id
    return ids


# A decisão da síndica sobre as duas anomalias, usando o mesmo review_anomaly que a API vai usar.
def apply_demo_reviews(db: Session, ids: DemoIds) -> None:
    # A síndica revisa a fila de anomalias: libera S0 e descarta S6.
    # O import fica dentro da função: o faturamento só é carregado quando a revisão é de fato usada.
    from backend.faturamento.service import review_anomaly

    review_anomaly(
        db,
        ids.anomalies["S0"],
        AnomalyStatus.APPROVED,
        ids.users["manager"],
        "Morador comprovou recarga completa após viagem; energia coerente com 7 kW.",
    )
    review_anomaly(
        db,
        ids.anomalies["S6"],
        AnomalyStatus.REJECTED,
        ids.users["manager"],
        "Medição impossível para o carregador de 7 kW; registro corrompido, não cobrar.",
    )
