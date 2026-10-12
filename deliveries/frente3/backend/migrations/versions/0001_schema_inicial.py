"""Schema inicial do EV ChargeOps (Frente 3 - Banco de dados e motor de rateio).

Cria as 10 entidades do plano da Sprint 2 (User, CondoUnit, Charger,
Reservation, ChargingSession, Tariff, Invoice, InvoiceItem, Anomaly,
AuditEvent) e seis tabelas de apoio (rfid_cards, session_power_samples,
tariff_bands, tariff_windows, tax_rules, holidays).

As regras de integridade do plano são garantidas pelo próprio PostgreSQL,
e não só pelo código Python:

  1. Uma sessão não pode ser cobrada para dois moradores
     -> UNIQUE(invoice_items.session_id) + chaves estrangeiras compostas.
  2. Reservas do mesmo carregador não se sobrepõem além da capacidade
     -> EXCLUDE USING gist por (carregador, conector, intervalo) + gatilho de capacidade.
  3. Tarifas versionadas / com validade temporal
     -> EXCLUDE de vigências sobrepostas + gatilho que impede alterar tarifa já faturada.
  4. Fatura fechada não muda silenciosamente
     -> gatilhos que bloqueiam UPDATE/DELETE em faturas e itens fechados.
  5. Revisão manual de anomalia deixa evento de auditoria
     -> gatilho em anomalies que grava audit_events (tabela somente-inserção).

Revision ID: 0001_schema_inicial
Revises: (nenhuma)
"""

# O arquivo é Python, mas quase todo o conteúdo é SQL, a linguagem do banco de dados.
# O Python funciona como um envelope: guarda o SQL em textos e entrega esses textos ao PostgreSQL.
#
# Por que há tantos """:
# - o primeiro par, lá em cima, abre e fecha a docstring (a documentação do arquivo);
# - cada bloco SQL_... = """ ... """ é um texto de várias linhas guardado numa variável, e cada texto
#   precisa de um """ para abrir e outro para fechar (6 blocos x 2 = 12).
#   As aspas triplas aceitam quebras de linha e aspas simples dentro do texto ('active', '[)'),
#   sem precisar escapar nada. O Python não executa esse SQL: só guarda o texto.
#
# São três camadas, uma dentro da outra:
#   Python  -> o texto entre """ ... """ (comentários com #)
#   SQL     -> CREATE TABLE, CHECK, EXCLUDE... (dentro dos textos, comentários com --, e não com #)
#   plpgsql -> o código dos gatilhos, entre $$ ... $$ (a linguagem de programação que roda no PostgreSQL)
#
# No fim do arquivo, upgrade() entrega os 5 blocos ao banco, nesta ordem. A ordem importa: uma tabela
# só pode apontar para outra que já existe (users aponta para condo_units, então condo_units vem antes).


# op: a ferramenta do Alembic que entrega comandos ao banco (op.execute).
from alembic import op

# "Identidade" desta migration. O Alembic usa esses nomes para saber a ordem das migrations:
# down_revision = None quer dizer que esta é a primeira. Uma futura 0002 teria down_
revision = "0001_schema_inicial"
down_revision = None
branch_labels = None
depends_on = None


# 1. Extensão e cadastros básicos

SQL_CADASTROS = """
-- btree_gist permite misturar igualdade (=) e sobreposição de intervalos (&&)
-- na mesma restrição EXCLUDE. É o que impede reservas e sessões sobrepostas.
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE condo_units (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    block       TEXT NOT NULL DEFAULT '',
    number      TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_condo_units_block_number UNIQUE (block, number)
);

CREATE TABLE users (
    id                         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                       TEXT NOT NULL,
    email                      TEXT NOT NULL,
    role                       TEXT NOT NULL,
    unit_id                    BIGINT REFERENCES condo_units (id),
    password_hash              TEXT,
    active                     BOOLEAN NOT NULL DEFAULT true,
    reservation_blocked_until  TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_email_lowercase CHECK (email = lower(email)),
    CONSTRAINT ck_users_role CHECK (role IN ('resident', 'manager')),
    -- Todo morador pertence a uma unidade; o gestor pode ser externo (administradora).
    CONSTRAINT ck_users_resident_has_unit CHECK (role <> 'resident' OR unit_id IS NOT NULL)
);

CREATE TABLE chargers (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL,               -- "charger_id" do SessionDTO (ex.: HCA01)
    serial_number   TEXT NOT NULL,
    model           TEXT NOT NULL,               -- ex.: GW7K-HCA-20
    rated_power_kw  NUMERIC(5,2) NOT NULL,       -- potência nominal (7, 11 ou 22 kW)
    connectors      SMALLINT NOT NULL DEFAULT 1, -- capacidade simultânea configurada
    location        TEXT,
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_chargers_code UNIQUE (code),
    CONSTRAINT uq_chargers_serial_number UNIQUE (serial_number),
    CONSTRAINT ck_chargers_rated_power CHECK (rated_power_kw > 0),
    CONSTRAINT ck_chargers_connectors CHECK (connectors >= 1)
);

-- Pool de cartões RFID do condomínio (até 10 por HCA G2), sob custódia do síndico.
-- A identidade do morador vive na reserva, não no cartão (decisão da Sprint 1).
CREATE TABLE rfid_cards (
    card_uid           TEXT PRIMARY KEY,         -- "card_id" do SessionDTO
    label              TEXT NOT NULL,
    custodian_user_id  BIGINT NOT NULL REFERENCES users (id),
    active             BOOLEAN NOT NULL DEFAULT true,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


# 2. Reservas e sessões de recarga
SQL_OPERACAO = """
CREATE TABLE reservations (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users (id),
    charger_id    BIGINT NOT NULL REFERENCES chargers (id),
    connector     SMALLINT NOT NULL DEFAULT 1,
    starts_at     TIMESTAMPTZ NOT NULL,
    ends_at       TIMESTAMPTZ NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    cancelled_at  TIMESTAMPTZ,
    -- alvo da FK composta de charging_sessions (sessão x dono da reserva)
    CONSTRAINT uq_reservations_id_user UNIQUE (id, user_id),
    CONSTRAINT ck_reservations_period CHECK (ends_at > starts_at),
    CONSTRAINT ck_reservations_connector CHECK (connector >= 1),
    CONSTRAINT ck_reservations_status
        CHECK (status IN ('active', 'in_use', 'completed', 'cancelled', 'no_show')),
    -- REGRA DE INTEGRIDADE 2: duas reservas ativas não ocupam o mesmo conector
    -- no mesmo horário. Com N conectores, cabem no máximo N reservas simultâneas.
    CONSTRAINT ex_reservations_no_overlap EXCLUDE USING gist (
        charger_id WITH =,
        connector  WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    ) WHERE (status IN ('active', 'in_use'))
);
CREATE INDEX ix_reservations_user_starts ON reservations (user_id, starts_at);

CREATE TABLE charging_sessions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source              TEXT NOT NULL,
    external_id         TEXT NOT NULL,           -- "session_id" do SessionDTO
    charger_id          BIGINT NOT NULL REFERENCES chargers (id),
    connector           SMALLINT NOT NULL DEFAULT 1,
    card_id             TEXT,
    reservation_id      BIGINT,
    user_id             BIGINT REFERENCES users (id),
    attribution_method  TEXT NOT NULL DEFAULT 'unattributed',
    started_at          TIMESTAMPTZ NOT NULL,
    energy_ended_at     TIMESTAMPTZ,             -- fim do fluxo de energia (base da ociosidade)
    ended_at            TIMESTAMPTZ,             -- fim da ocupação (desconexão)
    total_kwh           NUMERIC(10,3) NOT NULL DEFAULT 0,
    green_kwh           NUMERIC(10,3) NOT NULL DEFAULT 0,
    grid_kwh            NUMERIC(10,3) NOT NULL DEFAULT 0,
    average_power_kw    NUMERIC(6,2),
    max_power_kw        NUMERIC(6,2),
    end_status          TEXT NOT NULL DEFAULT 'in_progress',
    failure_code        TEXT,
    validation_status   TEXT NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sessions_source_external UNIQUE (source, external_id),
    -- alvo da FK composta de invoice_items (item x dono da sessão)
    CONSTRAINT uq_sessions_id_user UNIQUE (id, user_id),
    -- Sessão atribuída por reserva pertence ao dono da reserva.
    CONSTRAINT fk_sessions_reservation_same_user FOREIGN KEY (reservation_id, user_id)
        REFERENCES reservations (id, user_id),
    CONSTRAINT ck_sessions_source CHECK (source IN ('sems', 'gateway', 'simulator')),
    CONSTRAINT ck_sessions_attribution
        CHECK (attribution_method IN ('unattributed', 'reservation', 'card_custodian', 'manual')),
    CONSTRAINT ck_sessions_attribution_user
        CHECK ((attribution_method = 'unattributed') = (user_id IS NULL)),
    CONSTRAINT ck_sessions_reservation_requires_user
        CHECK (reservation_id IS NULL OR user_id IS NOT NULL),
    CONSTRAINT ck_sessions_attribution_by_reservation
        CHECK (attribution_method <> 'reservation' OR reservation_id IS NOT NULL),
    CONSTRAINT ck_sessions_end_status
        CHECK (end_status IN ('in_progress', 'completed', 'user_stopped', 'system_failure')),
    CONSTRAINT ck_sessions_validation_status
        CHECK (validation_status IN ('pending', 'approved', 'suspended', 'rejected')),
    CONSTRAINT ck_sessions_in_progress_not_validated
        CHECK (end_status <> 'in_progress' OR validation_status = 'pending'),
    CONSTRAINT ck_sessions_energy_non_negative
        CHECK (total_kwh >= 0 AND green_kwh >= 0 AND grid_kwh >= 0),
    CONSTRAINT ck_sessions_finished_has_end
        CHECK ((end_status = 'in_progress') = (ended_at IS NULL)),
    CONSTRAINT ck_sessions_time_order CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT ck_sessions_energy_end_order CHECK (
        energy_ended_at IS NULL
        OR (energy_ended_at >= started_at AND (ended_at IS NULL OR energy_ended_at <= ended_at))
    ),
    CONSTRAINT ck_sessions_connector CHECK (connector >= 1),
    -- Regra física: um conector não entrega energia a duas sessões ao mesmo tempo.
    -- Isso também impede que SEMS e gateway gravem duas vezes a mesma recarga
    -- (a reconciliação da Frente 1/2 deve atualizar a sessão existente).
    CONSTRAINT ex_sessions_no_overlap EXCLUDE USING gist (
        charger_id WITH =,
        connector  WITH =,
        tstzrange(started_at, ended_at, '[)') WITH &&
    )
);
CREATE INDEX ix_sessions_user_started ON charging_sessions (user_id, started_at);
CREATE INDEX ix_sessions_validation ON charging_sessions (validation_status);

-- Curva de potência da sessão (aba Operation Monitoring da SEMS / leitura Modbus).
-- Usada para dividir a energia entre faixas horárias e pela IA (Frente 4).
CREATE TABLE session_power_samples (
    session_id      BIGINT NOT NULL REFERENCES charging_sessions (id) ON DELETE CASCADE,
    measured_at     TIMESTAMPTZ NOT NULL,
    power_kw        NUMERIC(7,3) NOT NULL,
    green_power_kw  NUMERIC(7,3),              -- opcional: parcela solar/bateria no instante
    PRIMARY KEY (session_id, measured_at),
    CONSTRAINT ck_samples_power CHECK (power_kw >= 0 AND (green_power_kw IS NULL OR green_power_kw >= 0))
);
"""


# 3. Parâmetros de cobrança: tarifas versionadas, impostos e feriados

SQL_PARAMETROS = """
-- Cada linha é uma versão da tabela tarifária aprovada pela assembleia.
CREATE TABLE tariffs (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                        TEXT NOT NULL,
    valid_from                  TIMESTAMPTZ NOT NULL,
    valid_to                    TIMESTAMPTZ,       -- NULL = vigente sem data de término
    idle_tolerance_minutes      INTEGER NOT NULL DEFAULT 15,
    idle_fee_per_minute         NUMERIC(8,4) NOT NULL,
    overhead_percent            NUMERIC(5,2) NOT NULL DEFAULT 0,
    weekends_holidays_off_peak  BOOLEAN NOT NULL DEFAULT true,
    assembly_reference          TEXT,             -- ex.: "Ata da AGE de 10/08/2026"
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tariffs_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ck_tariffs_idle CHECK (idle_tolerance_minutes >= 0 AND idle_fee_per_minute >= 0),
    CONSTRAINT ck_tariffs_overhead CHECK (overhead_percent >= 0 AND overhead_percent <= 100),
    -- REGRA DE INTEGRIDADE 3: em cada instante existe no máximo uma tabela vigente.
    CONSTRAINT ex_tariffs_no_overlap EXCLUDE USING gist (
        tstzrange(valid_from, valid_to, '[)') WITH &&
    )
);

-- Preço Green e Grid de cada faixa, dentro de uma versão de tarifa.
CREATE TABLE tariff_bands (
    tariff_id            BIGINT NOT NULL REFERENCES tariffs (id) ON DELETE CASCADE,
    band                 TEXT NOT NULL,
    green_price_per_kwh  NUMERIC(8,4) NOT NULL,
    grid_price_per_kwh   NUMERIC(8,4) NOT NULL,
    PRIMARY KEY (tariff_id, band),
    CONSTRAINT ck_tariff_bands_band CHECK (band IN ('off_peak', 'intermediate', 'peak')),
    CONSTRAINT ck_tariff_bands_prices CHECK (green_price_per_kwh >= 0 AND grid_price_per_kwh >= 0)
);

-- Janelas de ponta e intermediário nos dias úteis. Todo horário fora delas é
-- fora de ponta. Janelas não atravessam a meia-noite.
CREATE TABLE tariff_windows (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tariff_id   BIGINT NOT NULL REFERENCES tariffs (id) ON DELETE CASCADE,
    band        TEXT NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    CONSTRAINT ck_tariff_windows_band CHECK (band IN ('intermediate', 'peak')),
    CONSTRAINT ck_tariff_windows_order CHECK (end_time > start_time),
    -- a janela só pode usar uma faixa que tenha preço definido na mesma tarifa
    CONSTRAINT fk_tariff_windows_band FOREIGN KEY (tariff_id, band)
        REFERENCES tariff_bands (tariff_id, band) ON DELETE CASCADE,
    CONSTRAINT ex_tariff_windows_no_overlap EXCLUDE USING gist (
        tariff_id WITH =,
        tsrange(DATE '2000-01-01' + start_time, DATE '2000-01-01' + end_time, '[)') WITH &&
    )
);

-- Imposto parametrizável por jurisdição e período (Frente 2: ICMS x ISS hoje,
-- IBS/CBS na transição). Tipos diferentes podem valer ao mesmo tempo.
CREATE TABLE tax_rules (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tax_type                    TEXT NOT NULL,
    jurisdiction                TEXT NOT NULL,
    rate_percent                NUMERIC(6,3) NOT NULL,
    -- Exclui a energia compensada (Green) da base de cálculo. Só deve ser
    -- ligado quando a modalidade de geração permitir (LC 214/2025, art. 28;
    -- Decreto 12.955/2026, art. 15), conforme análise da Frente 2.
    exclude_compensated_energy  BOOLEAN NOT NULL DEFAULT false,
    legal_basis                 TEXT,
    valid_from                  TIMESTAMPTZ NOT NULL,
    valid_to                    TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_tax_rules_type CHECK (tax_type IN ('icms', 'iss', 'ibs', 'cbs')),
    CONSTRAINT ck_tax_rules_rate CHECK (rate_percent >= 0 AND rate_percent <= 100),
    CONSTRAINT ck_tax_rules_validity CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT ex_tax_rules_no_overlap EXCLUDE USING gist (
        jurisdiction WITH =,
        tax_type     WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    )
);

-- Feriados: se a tarifa assim definir, o dia inteiro é fora de ponta (Tarifa Branca).
CREATE TABLE holidays (
    holiday_date  DATE PRIMARY KEY,
    description   TEXT NOT NULL
);
"""


# 4. Faturas, anomalias e auditoria

SQL_FATURAMENTO = """
CREATE TABLE invoices (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users (id),
    period           DATE NOT NULL,                  -- 1º dia do mês de referência
    status           TEXT NOT NULL DEFAULT 'open',
    sessions_count   INTEGER NOT NULL DEFAULT 0,
    green_kwh        NUMERIC(12,3) NOT NULL DEFAULT 0,
    grid_kwh         NUMERIC(12,3) NOT NULL DEFAULT 0,
    idle_minutes     INTEGER NOT NULL DEFAULT 0,
    green_amount     NUMERIC(12,2) NOT NULL DEFAULT 0,
    grid_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    idle_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    subtotal         NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount       NUMERIC(12,2) NOT NULL DEFAULT 0,
    overhead_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    total            NUMERIC(12,2) NOT NULL DEFAULT 0,
    calculation      JSONB NOT NULL DEFAULT '{}'::jsonb,  -- memória de cálculo da fatura
    engine_version   TEXT NOT NULL,
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at        TIMESTAMPTZ,
    -- dois veículos da mesma unidade = dois moradores = duas faturas
    CONSTRAINT uq_invoices_user_period UNIQUE (user_id, period),
    CONSTRAINT uq_invoices_id_user UNIQUE (id, user_id),
    CONSTRAINT ck_invoices_period_first_day CHECK (EXTRACT(DAY FROM period) = 1),
    CONSTRAINT ck_invoices_status CHECK (status IN ('open', 'closed')),
    CONSTRAINT ck_invoices_closed_at CHECK ((status = 'closed') = (closed_at IS NOT NULL)),
    CONSTRAINT ck_invoices_non_negative CHECK (
        green_amount >= 0 AND grid_amount >= 0 AND idle_amount >= 0
        AND tax_amount >= 0 AND overhead_amount >= 0
    ),
    -- A aritmética da fatura é garantida pelo banco.
    CONSTRAINT ck_invoices_subtotal CHECK (subtotal = green_amount + grid_amount + idle_amount),
    CONSTRAINT ck_invoices_total CHECK (total = subtotal + tax_amount + overhead_amount)
);

-- Uma linha por sessão faturada. Guarda os valores e a memória de cálculo
-- (JSONB) no momento do cálculo: mudar a tarifa depois não altera o item.
CREATE TABLE invoice_items (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id       BIGINT NOT NULL,
    user_id          BIGINT NOT NULL,
    session_id       BIGINT NOT NULL,
    tariff_id        BIGINT REFERENCES tariffs (id),
    tax_rule_ids     BIGINT[] NOT NULL DEFAULT '{}',
    charge_rule      TEXT NOT NULL,
    is_late_entry    BOOLEAN NOT NULL DEFAULT false,  -- sessão de mês anterior liberada depois
    green_kwh        NUMERIC(10,3) NOT NULL,
    grid_kwh         NUMERIC(10,3) NOT NULL,
    idle_minutes     INTEGER NOT NULL,
    green_amount     NUMERIC(12,2) NOT NULL,
    grid_amount      NUMERIC(12,2) NOT NULL,
    idle_amount      NUMERIC(12,2) NOT NULL,
    subtotal         NUMERIC(12,2) NOT NULL,
    tax_amount       NUMERIC(12,2) NOT NULL,
    overhead_amount  NUMERIC(12,2) NOT NULL,
    total            NUMERIC(12,2) NOT NULL,
    calculation      JSONB NOT NULL,                  -- memória de cálculo da sessão
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- REGRA DE INTEGRIDADE 1: cada sessão é cobrada uma única vez...
    CONSTRAINT uq_invoice_items_session UNIQUE (session_id),
    -- ...e somente do morador dono da sessão (as duas FKs compartilham user_id).
    CONSTRAINT fk_items_invoice_same_user FOREIGN KEY (invoice_id, user_id)
        REFERENCES invoices (id, user_id) ON DELETE CASCADE,
    CONSTRAINT fk_items_session_same_user FOREIGN KEY (session_id, user_id)
        REFERENCES charging_sessions (id, user_id),
    CONSTRAINT ck_items_charge_rule
        CHECK (charge_rule IN ('normal', 'user_stopped_no_idle', 'system_failure_no_charge')),
    CONSTRAINT ck_items_non_negative CHECK (
        green_amount >= 0 AND grid_amount >= 0 AND idle_amount >= 0
        AND tax_amount >= 0 AND overhead_amount >= 0
    ),
    CONSTRAINT ck_items_subtotal CHECK (subtotal = green_amount + grid_amount + idle_amount),
    CONSTRAINT ck_items_total CHECK (total = subtotal + tax_amount + overhead_amount),
    -- Casos excepcionais da Sprint 1 também garantidos no banco:
    CONSTRAINT ck_items_failure_is_free
        CHECK (charge_rule <> 'system_failure_no_charge' OR total = 0),
    CONSTRAINT ck_items_idle_only_when_normal
        CHECK (charge_rule = 'normal' OR (idle_amount = 0 AND idle_minutes = 0))
);
CREATE INDEX ix_invoice_items_invoice ON invoice_items (invoice_id);
CREATE INDEX ix_invoice_items_tariff ON invoice_items (tariff_id);

CREATE TABLE anomalies (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id   BIGINT NOT NULL REFERENCES charging_sessions (id),
    detected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    detector     TEXT NOT NULL,          -- ex.: physical_rule, isolation_forest, lof
    score        NUMERIC(10,4),
    reasons      JSONB NOT NULL DEFAULT '[]'::jsonb,
    status       TEXT NOT NULL DEFAULT 'pending_review',
    reviewed_by  BIGINT REFERENCES users (id),
    reviewed_at  TIMESTAMPTZ,
    review_note  TEXT,
    CONSTRAINT uq_anomalies_session UNIQUE (session_id),
    CONSTRAINT ck_anomalies_status CHECK (status IN ('pending_review', 'approved', 'rejected')),
    -- Decisão sempre com responsável e data (LGPD art. 20: revisão humana rastreável).
    CONSTRAINT ck_anomalies_review_fields CHECK (
        (status = 'pending_review') = (reviewed_by IS NULL)
        AND (status = 'pending_review') = (reviewed_at IS NULL)
    )
);
CREATE INDEX ix_anomalies_status ON anomalies (status);

-- Trilha de auditoria: alterações financeiras, revisões de anomalia e
-- divergências de reconciliação SEMS x gateway. Somente inserção.
CREATE TABLE audit_events (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_user_id  BIGINT REFERENCES users (id),      -- NULL = ação do sistema
    entity_type    TEXT NOT NULL,
    entity_id      TEXT NOT NULL,
    action         TEXT NOT NULL,
    before_data    JSONB,
    after_data     JSONB,
    reason         TEXT
);
CREATE INDEX ix_audit_events_entity ON audit_events (entity_type, entity_id);
CREATE INDEX ix_audit_events_occurred ON audit_events (occurred_at);
"""


# 5. Gatilhos (triggers) que completam as regras de integridade

SQL_GATILHOS = """
-- updated_at automático nas sessões
CREATE FUNCTION fn_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON charging_sessions
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- Capacidade configurada: o conector usado precisa existir no carregador.
CREATE FUNCTION fn_check_connector_capacity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_connectors SMALLINT;
BEGIN
    SELECT connectors INTO v_connectors FROM chargers WHERE id = NEW.charger_id;
    IF v_connectors IS NOT NULL AND NEW.connector > v_connectors THEN
        RAISE EXCEPTION 'Conector % não existe no carregador % (capacidade configurada: % conector(es))',
            NEW.connector, NEW.charger_id, v_connectors
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_reservations_connector
    BEFORE INSERT OR UPDATE OF charger_id, connector ON reservations
    FOR EACH ROW EXECUTE FUNCTION fn_check_connector_capacity();

CREATE TRIGGER trg_sessions_connector
    BEFORE INSERT OR UPDATE OF charger_id, connector ON charging_sessions
    FOR EACH ROW EXECUTE FUNCTION fn_check_connector_capacity();

-- Auditoria é somente inserção.
CREATE FUNCTION fn_forbid_audit_changes() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_events é somente inserção: eventos de auditoria não podem ser alterados nem apagados'
        USING ERRCODE = 'integrity_constraint_violation';
END $$;

CREATE TRIGGER trg_audit_events_append_only
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION fn_forbid_audit_changes();

-- REGRA DE INTEGRIDADE 4 (parte 1): fatura fechada é imutável, e só fecha se
-- os totais conferem com a soma dos itens e todas as sessões estão aprovadas.
CREATE FUNCTION fn_protect_invoice() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v RECORD;
    v_not_approved INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status = 'closed' THEN
            RAISE EXCEPTION 'Fatura % está fechada e não pode ser apagada', OLD.id
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.status = 'closed' THEN
        RAISE EXCEPTION 'Fatura % está fechada: alterações não são permitidas (lance ajustes na fatura seguinte)',
            OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF NEW.status = 'closed' THEN
        SELECT count(*)                          AS n,
               coalesce(sum(green_kwh), 0)       AS green_kwh,
               coalesce(sum(grid_kwh), 0)        AS grid_kwh,
               coalesce(sum(idle_minutes), 0)    AS idle_minutes,
               coalesce(sum(green_amount), 0)    AS green_amount,
               coalesce(sum(grid_amount), 0)     AS grid_amount,
               coalesce(sum(idle_amount), 0)     AS idle_amount,
               coalesce(sum(tax_amount), 0)      AS tax_amount,
               coalesce(sum(overhead_amount), 0) AS overhead_amount
          INTO v
          FROM invoice_items
         WHERE invoice_id = NEW.id;

        IF v.n <> NEW.sessions_count
           OR v.green_kwh <> NEW.green_kwh OR v.grid_kwh <> NEW.grid_kwh
           OR v.idle_minutes <> NEW.idle_minutes
           OR v.green_amount <> NEW.green_amount OR v.grid_amount <> NEW.grid_amount
           OR v.idle_amount <> NEW.idle_amount OR v.tax_amount <> NEW.tax_amount
           OR v.overhead_amount <> NEW.overhead_amount THEN
            RAISE EXCEPTION 'Fatura % não pode ser fechada: os totais não conferem com a soma dos itens', NEW.id
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;

        SELECT count(*) INTO v_not_approved
          FROM invoice_items i
          JOIN charging_sessions s ON s.id = i.session_id
         WHERE i.invoice_id = NEW.id AND s.validation_status <> 'approved';
        IF v_not_approved > 0 THEN
            RAISE EXCEPTION 'Fatura % não pode ser fechada: % sessão(ões) deixaram de estar aprovadas; recalcule',
                NEW.id, v_not_approved
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_invoices_protect
    BEFORE UPDATE OR DELETE ON invoices
    FOR EACH ROW EXECUTE FUNCTION fn_protect_invoice();

-- REGRA DE INTEGRIDADE 4 (parte 2): itens de fatura fechada também são imutáveis.
CREATE FUNCTION fn_protect_invoice_items() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_ids BIGINT[];
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_ids := ARRAY[NEW.invoice_id];
    ELSIF TG_OP = 'UPDATE' THEN
        v_ids := ARRAY[OLD.invoice_id, NEW.invoice_id];
    ELSE
        v_ids := ARRAY[OLD.invoice_id];
    END IF;

    IF EXISTS (SELECT 1 FROM invoices WHERE id = ANY (v_ids) AND status = 'closed') THEN
        RAISE EXCEPTION 'Itens de fatura fechada não podem ser incluídos, alterados ou removidos'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_invoice_items_protect
    BEFORE INSERT OR UPDATE OR DELETE ON invoice_items
    FOR EACH ROW EXECUTE FUNCTION fn_protect_invoice_items();

-- Sessão suspeita não entra na fatura: só sessões aprovadas e encerradas.
CREATE FUNCTION fn_require_billable_session() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_validation TEXT;
    v_end_status TEXT;
BEGIN
    SELECT validation_status, end_status INTO v_validation, v_end_status
      FROM charging_sessions WHERE id = NEW.session_id;
    IF v_validation IS DISTINCT FROM 'approved' THEN
        RAISE EXCEPTION 'Sessão % não pode entrar na fatura: validação = % (precisa ser approved)',
            NEW.session_id, v_validation
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF v_end_status = 'in_progress' THEN
        RAISE EXCEPTION 'Sessão % ainda está em andamento e não pode ser faturada', NEW.session_id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_invoice_items_billable_session
    BEFORE INSERT OR UPDATE OF session_id ON invoice_items
    FOR EACH ROW EXECUTE FUNCTION fn_require_billable_session();

-- REGRA DE INTEGRIDADE 5: detecção e revisão de anomalia sempre deixam
-- evento de auditoria e mantêm o status da sessão coerente com a decisão.
CREATE FUNCTION fn_anomaly_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_events (actor_user_id, entity_type, entity_id, action, after_data, reason)
        VALUES (NULL, 'anomaly', NEW.id::text, 'anomaly_detected',
                jsonb_build_object('session_id', NEW.session_id, 'detector', NEW.detector,
                                   'score', NEW.score, 'status', NEW.status),
                'Sessão suspensa automaticamente para revisão humana');
        IF NEW.status = 'pending_review' THEN
            UPDATE charging_sessions SET validation_status = 'suspended' WHERE id = NEW.session_id;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO audit_events (actor_user_id, entity_type, entity_id, action,
                                  before_data, after_data, reason)
        VALUES (NEW.reviewed_by, 'anomaly', NEW.id::text, 'anomaly_review',
                jsonb_build_object('status', OLD.status, 'session_id', OLD.session_id),
                jsonb_build_object('status', NEW.status, 'session_id', NEW.session_id,
                                   'reviewed_at', NEW.reviewed_at),
                NEW.review_note);
        UPDATE charging_sessions
           SET validation_status = CASE NEW.status
                                       WHEN 'approved' THEN 'approved'
                                       WHEN 'rejected' THEN 'rejected'
                                       ELSE 'suspended'
                                   END
         WHERE id = NEW.session_id;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_anomalies_audit
    AFTER INSERT OR UPDATE OF status ON anomalies
    FOR EACH ROW EXECUTE FUNCTION fn_anomaly_audit();

-- REGRA DE INTEGRIDADE 3 (parte 2): tarifa ou regra de imposto já usada em
-- fatura não muda; o único ajuste permitido é encerrar a vigência (valid_to).
CREATE FUNCTION fn_protect_used_parameters() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_id    BIGINT;
    v_used  BOOLEAN;
BEGIN
    IF TG_TABLE_NAME IN ('tariffs', 'tax_rules') THEN
        v_id := OLD.id;
    ELSIF TG_OP = 'INSERT' THEN
        v_id := NEW.tariff_id;
    ELSE
        v_id := OLD.tariff_id;
    END IF;

    IF TG_TABLE_NAME = 'tax_rules' THEN
        SELECT EXISTS (SELECT 1 FROM invoice_items WHERE v_id = ANY (tax_rule_ids)) INTO v_used;
    ELSE
        SELECT EXISTS (SELECT 1 FROM invoice_items WHERE tariff_id = v_id) INTO v_used;
    END IF;

    IF v_used THEN
        IF TG_OP = 'UPDATE' AND TG_TABLE_NAME IN ('tariffs', 'tax_rules')
           AND (to_jsonb(NEW) - 'valid_to') = (to_jsonb(OLD) - 'valid_to') THEN
            RETURN NEW;  -- apenas encerrar a vigência
        END IF;
        RAISE EXCEPTION '% % já foi usada em faturas: crie uma nova versão com nova vigência em vez de alterar',
            TG_TABLE_NAME, v_id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_tariffs_protect
    BEFORE UPDATE OR DELETE ON tariffs
    FOR EACH ROW EXECUTE FUNCTION fn_protect_used_parameters();
CREATE TRIGGER trg_tariff_bands_protect
    BEFORE INSERT OR UPDATE OR DELETE ON tariff_bands
    FOR EACH ROW EXECUTE FUNCTION fn_protect_used_parameters();
CREATE TRIGGER trg_tariff_windows_protect
    BEFORE INSERT OR UPDATE OR DELETE ON tariff_windows
    FOR EACH ROW EXECUTE FUNCTION fn_protect_used_parameters();
CREATE TRIGGER trg_tax_rules_protect
    BEFORE UPDATE OR DELETE ON tax_rules
    FOR EACH ROW EXECUTE FUNCTION fn_protect_used_parameters();
"""

# Desfaz tudo o que o upgrade criou (a "demolição"), usado para recriar o banco do zero.
SQL_DOWNGRADE = """
DROP TABLE IF EXISTS audit_events, anomalies, invoice_items, invoices, holidays, tax_rules,
    tariff_windows, tariff_bands, tariffs, session_power_samples, charging_sessions,
    reservations, rfid_cards, chargers, users, condo_units CASCADE;
DROP FUNCTION IF EXISTS fn_set_updated_at(), fn_check_connector_capacity(),
    fn_forbid_audit_changes(), fn_protect_invoice(), fn_protect_invoice_items(),
    fn_require_billable_session(), fn_anomaly_audit(), fn_protect_used_parameters();
"""

# Chamado por "alembic upgrade head": entrega os 5 blocos ao banco, na ordem.
def upgrade() -> None:
    op.execute(SQL_CADASTROS)
    op.execute(SQL_OPERACAO)
    op.execute(SQL_PARAMETROS)
    op.execute(SQL_FATURAMENTO)
    op.execute(SQL_GATILHOS)

# Chamado por "alembic downgrade base": apaga tudo.
def downgrade() -> None:
    op.execute(SQL_DOWNGRADE)
