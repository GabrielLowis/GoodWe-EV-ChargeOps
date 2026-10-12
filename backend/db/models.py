## Modelos ORM (SQLAlchemy 2.0) das tabelas criadas na migration 0001. ##

""" A migration é a fonte da verdade do schema (inclui CHECK, EXCLUDE e gatilhos).
Estes modelos espelham colunas, chaves e índices para uso no código Python;
o teste backend/tests/db/test_migrations.py confere que os dois não divergem.
"""

# Faz o Python guardar as anotações de tipo como texto e só lê-las depois. Com as devidas anotacoes de data e typing
from __future__ import annotations
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

# SQL importanto o necessario para as anotacoes
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
# Tipos que só o PostgreSQL tem: ARRAY (lista dentro de uma coluna) e JSONB (JSON guardado pelo banco).
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
# Mapped (tipo do atributo), mapped_column (detalhes da coluna) e relationship (ligação entre objetos).
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Classe-mãe definida em base.py: toda classe que herda dela vira uma tabela.
from backend.db.base import Base

# Coluna id usada na maioria das tabelas: inteiro grande, chave primária, numerada pelo próprio banco.
def _pk() -> Mapped[int]:
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)

# Coluna "criado em": data e hora com fuso, obrigatória, preenchida pelo banco (now()) ao inserir a linha.
def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


## REALIZANDO OS CADASTROS

# Por apartamento
class CondoUnit(Base):
    __tablename__ = "condo_units"
    # Não pode haver duas unidades com o mesmo bloco e número. A vírgula antes do ")" é obrigatória: é ela
    __table_args__ = (UniqueConstraint("block", "number", name="uq_condo_units_block_number"),)

    id: Mapped[int] = _pk()
    # Valor que o próprio BANCO coloca quando ninguém informa ('' = condomínio sem blocos).
    block: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    number: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()
    # Lista de moradores da unidade. back_populates liga este lado ao User.unit: os dois ficam sempre de acordo.
    residents: Mapped[list[User]] = relationship(back_populates="unit")
    
    # @property cria um atributo calculado
    @property
    def label(self) -> str:
        return f"{self.block}-{self.number}" if self.block else self.number

# Por morador/Sindico
class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = _pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    # "resident" (morador) ou "manager" (síndico): os valores permitidos estão em enums.py.
    role: Mapped[str] = mapped_column(Text, nullable=False)
    # Chave estrangeira: aponta para o id de uma unidade. Pode ficar vazia só para o síndico
    unit_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("condo_units.id"))
    # Guarda só o hash da senha (uma versão embaralhada que não dá para desfazer), nunca a senha em si.
    password_hash: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Se preenchido, o morador não pode reservar até essa data (bloqueio por faltas; a regra é da Frente 2).
    reservation_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    # A unidade do morador: o outro lado de CondoUnit.residents.
    unit: Mapped[CondoUnit | None] = relationship(back_populates="residents")

# Carregador fisico - GoodWe HCA G2
class Charger(Base):
    __tablename__ = "chargers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_chargers_code"),
        UniqueConstraint("serial_number", name="uq_chargers_serial_number"),
    )

    id: Mapped[int] = _pk()
    code: Mapped[str] = mapped_column(Text, nullable=False)
    serial_number: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    # Numeric(5, 2): número decimal exato com até 5 dígitos, 2 depois da vírgula (ex.: 7.00 kW).
    rated_power_kw: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # Quantos carros ele carrega ao mesmo tempo (SmallInteger = inteiro pequeno).
    connectors: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    location: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()

# Por cartao RDID - Identidade do morador fica em sigilo
class RfidCard(Base):
    __tablename__ = "rfid_cards"

    # Aqui a chave primária é o próprio código do cartão (o "card_id" do SessionDTO), e não um id numérico.
    card_uid: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # Morador responsável pelo cartão: usado quando uma recarga não tem reserva (rede de segurança da Sprint 1).
    custodian_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _created_at()



# OPERACOES REALIZADAS

# Janela reservada por um morador em um conector de um carregador.
# (A regra "duas reservas ativas não podem se sobrepor no mesmo conector" é um EXCLUDE da migration.)
class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Parece repetido, porque o id sozinho já é único. Mas é este par que permite a chave composta da sessão (reservation_id, user_id), que garante que a sessão é do mesmo morador da reserva.
        UniqueConstraint("id", "user_id", name="uq_reservations_id_user"),
        # Índice: como o índice de um livro, acelera a busca "reservas deste morador, por data".
        Index("ix_reservations_user_starts", "user_id", "starts_at"),
    )

    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)  
    charger_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chargers.id"), nullable=False)
    connector: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # active, in_use, completed, cancelled ou no_show (enums.py). Em SQL, texto vai entre aspas simples: por isso "'active'" tem aspas dentro de aspas.
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  
    
# Sessão de recarga normalizada: o mesmo formato, venha do simulador, do gateway ou da SEMS.
class ChargingSession(Base):
    __tablename__ = "charging_sessions"
    __table_args__ = (
        # A mesma origem não consegue gravar a mesma sessão duas vezes (ex.: a integração reenviou o dado).
        UniqueConstraint("source", "external_id", name="uq_sessions_source_external"),
        # Permite a chave composta que vem de invoice_items (session_id, user_id).
        UniqueConstraint("id", "user_id", name="uq_sessions_id_user"),
        # Chave estrangeira composta: o par (reserva, morador) da sessão precisa existir em reservations.
        # Assim, uma sessão ligada a uma reserva é sempre do dono daquela reserva.
        ForeignKeyConstraint(
            ["reservation_id", "user_id"],
            ["reservations.id", "reservations.user_id"],
            name="fk_sessions_reservation_same_user",
        ),
        Index("ix_sessions_user_started", "user_id", "started_at"),  # sessões de um morador, por data
        Index("ix_sessions_validation", "validation_status"),  # sessões por status de validação
    )

    id: Mapped[int] = _pk()
    source: Mapped[str] = mapped_column(Text, nullable=False) 
    external_id: Mapped[str] = mapped_column(Text, nullable=False)  
    charger_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chargers.id"), nullable=False)
    connector: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    card_id: Mapped[str | None] = mapped_column(Text)  
    # Reserva ligada (vazio se não houve). Não tem ForeignKey aqui: a ligação é a chave composta lá em cima.
    reservation_id: Mapped[int | None] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))  
    # Como se descobriu o morador: reservation, card_custodian, manual ou unattributed (ainda sem morador).
    attribution_method: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'unattributed'"))
    # Três momentos: início, fim do fluxo de energia (a ociosidade conta a partir dele) e desconexão do carro.
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Energia em kWh com 3 casas depois da vírgula (resolução de 1 Wh): total, solar (Green) e da rede (Grid).
    total_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, server_default=text("0"))
    green_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, server_default=text("0"))
    grid_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, server_default=text("0"))
    average_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    max_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    # Como terminou: in_progress, completed, user_stopped ou system_failure (define a regra de cobrança).
    end_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'in_progress'"))
    failure_code: Mapped[str | None] = mapped_column(Text)  # código do erro, quando houve falha do sistema
    # pending, approved, suspended ou rejected. Só as aprovadas entram na fatura.
    validation_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    created_at: Mapped[datetime] = _created_at()
    # Atualizado sozinho por um gatilho do banco a cada alteração da sessão.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    charger: Mapped[Charger] = relationship()  # session.charger devolve o carregador da sessão
    # O user_id participa de duas chaves estrangeiras (a simples, para users, e a composta, para reservations).
    # foreign_keys diz ao SQLAlchemy qual das duas usar nesta ligação.
    user: Mapped[User | None] = relationship(foreign_keys=[user_id])
    # A curva de potência, em ordem de horário. cascade="all, delete-orphan": as medições pertencem à sessão
    # (são gravadas junto com ela e apagadas se saírem da lista).
    samples: Mapped[list[SessionPowerSample]] = relationship(
        back_populates="session",
        order_by="SessionPowerSample.measured_at",
        cascade="all, delete-orphan",
    )
    # A anomalia desta sessão, se houver. uselist=False devolve um objeto só (e não uma lista), porque cada sessão tem no máximo uma anomalia.
    anomaly: Mapped[Anomaly | None] = relationship(back_populates="session", uselist=False)


# Um ponto da curva de potência de uma sessão: uma medição num instante.
class SessionPowerSample(Base):
    __tablename__ = "session_power_samples"

    # Chave primária composta (sessão + horário): cada sessão tem no máximo uma medição por instante.
    # ondelete="CASCADE": se a sessão for apagada, o banco apaga as medições dela junto.
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("charging_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    power_kw: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)  
    green_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))  

    session: Mapped[ChargingSession] = relationship(back_populates="samples")



# PARÂMETROS DE COBRANÇA

# Versão da tabela tarifária aprovada pela assembleia, com validade no tempo. A migration impede duas versões valendo ao mesmo tempo e impede mudar o preço de uma tarifa que já entrou em fatura.
class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = _pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Vigência: vale de valid_from até valid_to (valid_to vazio = sem data de término).
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Minutos de tolerância antes de cobrar ociosidade (15 por padrão) e o valor por minuto depois deles.
    idle_tolerance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("15"))
    idle_fee_per_minute: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    # Percentual operacional do condomínio sobre o subtotal (0 por padrão).
    overhead_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default=text("0"))
    # True = sábados, domingos e feriados são inteiros fora de ponta.
    weekends_holidays_off_peak: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    assembly_reference: Mapped[str | None] = mapped_column(Text)  # ex.: "Ata da AGE de 10/08/2026"
    created_at: Mapped[datetime] = _created_at()

    # Os preços por faixa e as janelas pertencem à tarifa (cascade): são gravados e apagados junto com ela.
    bands: Mapped[list[TariffBand]] = relationship(back_populates="tariff", cascade="all, delete-orphan")
    windows: Mapped[list[TariffWindow]] = relationship(
        back_populates="tariff", cascade="all, delete-orphan", order_by="TariffWindow.start_time"
    )


# Preço Green e Grid de uma faixa (off_peak, intermediate, peak) numa versão da tarifa.
class TariffBand(Base):
    __tablename__ = "tariff_bands"

    # Chave primária composta (tarifa + faixa): cada faixa tem um preço só em cada versão da tarifa.
    tariff_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tariffs.id", ondelete="CASCADE"), primary_key=True)
    band: Mapped[str] = mapped_column(Text, primary_key=True)
    # Preços por kWh com 4 casas depois da vírgula: energia solar (Green) e da rede (Grid).
    green_price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    grid_price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    tariff: Mapped[Tariff] = relationship(back_populates="bands")


# Janela de dia útil em que vale a faixa intermediária ou a de ponta (fora das janelas, é fora de ponta).
# A migration também impede janelas sobrepostas na mesma tarifa.
class TariffWindow(Base):
    __tablename__ = "tariff_windows"
    __table_args__ = (
        # Chave composta (tarifa, faixa) -> tariff_bands: a janela só pode usar uma faixa que tenha preço
        # definido nesta mesma tarifa.
        ForeignKeyConstraint(
            ["tariff_id", "band"],
            ["tariff_bands.tariff_id", "tariff_bands.band"],
            name="fk_tariff_windows_band",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = _pk()
    tariff_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tariffs.id", ondelete="CASCADE"), nullable=False)
    band: Mapped[str] = mapped_column(Text, nullable=False)  
    # Time guarda só a hora do dia, ex.: 18:00.
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # O tariff_id participa de duas chaves estrangeiras; foreign_keys diz qual usar nesta ligação.
    tariff: Mapped[Tariff] = relationship(back_populates="windows", foreign_keys=[tariff_id])


# Imposto parametrizado por jurisdição e período (ICMS, ISS, IBS, CBS): muda por cadastro, sem mexer no código.
class TaxRule(Base):
    __tablename__ = "tax_rules"

    id: Mapped[int] = _pk()
    tax_type: Mapped[str] = mapped_column(Text, nullable=False)  
    jurisdiction: Mapped[str] = mapped_column(Text, nullable=False)  
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)  
    # True = o valor da energia solar compensada (Green) fica fora da base do imposto.
    exclude_compensated_energy: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    legal_basis: Mapped[str | None] = mapped_column(Text)  
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()


# Feriado nacional: nesses dias, a tarifa inteira é fora de ponta (lista da ANEEL em seeds/holidays.py).
class Holiday(Base):
    __tablename__ = "holidays"

    # A própria data é a chave primária: um registro por dia.
    holiday_date: Mapped[date] = mapped_column(Date, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)  


# FATURAMENTO, ANOMALIAS E AUDITORIA

# Fatura mensal de um morador.
class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_invoices_user_period"),  
        UniqueConstraint("id", "user_id", name="uq_invoices_id_user"),  
    )

    id: Mapped[int] = _pk()
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)  
    # "open" (ainda pode ser recalculada) ou "closed" (o banco recusa qualquer mudança).
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    sessions_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    green_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, server_default=text("0"))
    grid_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, server_default=text("0"))
    idle_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # Valores em reais: Numeric(12, 2) guarda os centavos exatos.
    green_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    grid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    idle_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    overhead_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default=text("0"))
    # Memória de cálculo da fatura, guardada como JSON (começa como {}, um dicionário vazio).
    calculation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    engine_version: Mapped[str] = mapped_column(Text, nullable=False)  # versão do motor que fez a conta
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # vazio enquanto estiver aberta

    user: Mapped[User] = relationship()
    # Os itens da fatura (uma linha por sessão), em ordem de id. A ligação usa a chave composta
    # (invoice_id, user_id), e cascade faz os itens serem gravados e apagados junto com a fatura.
    items: Mapped[list[InvoiceItem]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.id",
        foreign_keys="[InvoiceItem.invoice_id, InvoiceItem.user_id]",
    )


# Parcela da fatura: uma linha por sessão, com a sua memória de cálculo.
class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        # Uma sessão só pode ser cobrada uma vez.
        UniqueConstraint("session_id", name="uq_invoice_items_session"),
        # O item repete o user_id, e estas duas chaves compostas obrigam esse morador a ser, ao mesmo tempo,
        ForeignKeyConstraint(
            ["invoice_id", "user_id"],
            ["invoices.id", "invoices.user_id"],
            name="fk_items_invoice_same_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["session_id", "user_id"],
            ["charging_sessions.id", "charging_sessions.user_id"],
            name="fk_items_session_same_user",
        ),
        Index("ix_invoice_items_invoice", "invoice_id"),  
        Index("ix_invoice_items_tariff", "tariff_id"), 
    )

    id: Mapped[int] = _pk()
    invoice_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tariff_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tariffs.id")) 
    # Lista com os ids das regras de imposto usadas (ARRAY = lista numa coluna; começa vazia: '{}').
    tax_rule_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False, server_default=text("'{}'"))
    # normal, user_stopped_no_idle (sem ociosidade) ou system_failure_no_charge (valor zero).
    charge_rule: Mapped[str] = mapped_column(Text, nullable=False)
    # True = sessão de um mês anterior, cobrada neste mês depois de liberada na revisão.
    is_late_entry: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    green_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    grid_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    idle_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    green_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    grid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    idle_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    overhead_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    calculation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  
    created_at: Mapped[datetime] = _created_at()

    invoice: Mapped[Invoice] = relationship(back_populates="items", foreign_keys=[invoice_id, user_id])
    # viewonly: session_id e user_id são preenchidos explicitamente pelo serviço (viewonly = ligação só para leitura: serve para navegar de item.session até a sessão.)
    session: Mapped[ChargingSession] = relationship(foreign_keys=[session_id, user_id], viewonly=True)


# Sessão suspeita (saída da Frente 4) e a decisão de revisão do síndico. Na migration, um gatilho suspende a sessão quando a anomalia é criada e grava a auditoria quando o síndico decide.
class Anomaly(Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_anomalies_session"),  
        Index("ix_anomalies_status", "status"),  
    )

    id: Mapped[int] = _pk()
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("charging_sessions.id"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Quem detectou: ex.: "isolation_forest" (modelo de IA) ou "physical_rule" (regra física).
    detector: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))  # nota de suspeita do modelo (opcional)
    # Lista de motivos, guardada como JSON (começa como [], uma lista vazia).
    reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # pending_review (na fila do síndico), approved ou rejected.
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending_review'"))
    # Quem revisou, quando e com qual observação (vazios até a revisão).
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    session: Mapped[ChargingSession] = relationship(back_populates="anomaly")


# Evento da trilha de auditoria. Só aceita inserção: um gatilho da migration proíbe alterar ou apagar.
class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_id"),  
        Index("ix_audit_events_occurred", "occurred_at"),  
    )

    id: Mapped[int] = _pk()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))  
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)  
    action: Mapped[str] = mapped_column(Text, nullable=False) 
    # Como o registro estava antes e como ficou depois, em JSON.
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)  

