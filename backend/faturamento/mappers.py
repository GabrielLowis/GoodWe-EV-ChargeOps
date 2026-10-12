## Conversão dos modelos ORM para as estruturas puras do motor de rateio. ##

# Guarda as informacoes para o futuro
from __future__ import annotations
# Lista fechada das faixas horárias
from backend.db.enums import Band
#Modelos do banco: é deles que os dados saem.
from backend.db.models import ChargingSession, Tariff, TaxRule
# Estruturas do motor: é para elas que os dados vão.
from backend.rateio.models import BandPrice, PowerSample, SessionInput, TariffSpec, TaxRuleSpec, TimeWindow

# Tabela tarifária do banco -  TariffSpec do motor (preços por faixa, janelas, ociosidade e overhead).
def tariff_to_spec(tariff: Tariff) -> TariffSpec:
    return TariffSpec(
        id=tariff.id,
        name=tariff.name,
        # Vigência: a tabela vale de valid_from até valid_to (None = ainda sem data de término).
        valid_from=tariff.valid_from,
        valid_to=tariff.valid_to,
        # Decisão da assembleia que aprovou esta tabela
        assembly_reference=tariff.assembly_reference,
        # Monta um dicionário faixa 
        prices={Band(b.band): BandPrice(b.green_price_per_kwh, b.grid_price_per_kwh) for b in tariff.bands},
        # Janelas dos dias úteis
        windows=tuple(TimeWindow(Band(w.band), w.start_time, w.end_time) for w in tariff.windows),
        # Ociosidade: minutos de tolerância (15) e valor cobrado por minuto depois deles.
        idle_tolerance_minutes=tariff.idle_tolerance_minutes,
        idle_fee_per_minute=tariff.idle_fee_per_minute,
        # Percentual operacional do condomínio, aplicado sobre o subtotal (pode ser 0).
        overhead_percent=tariff.overhead_percent,
        # True = sábados, domingos e feriados são inteiros fora de ponta.
        weekends_holidays_off_peak=tariff.weekends_holidays_off_peak,
    )

# Regra de imposto do banco - TaxRuleSpec do motor. O imposto é um parâmetro, não um número fixo no código.
def tax_rule_to_spec(rule: TaxRule) -> TaxRuleSpec:
    return TaxRuleSpec(
        id=rule.id,
        # Qual imposto: icms, iss, ibs ou cbs.
        tax_type=rule.tax_type,
        # Alíquota em percentual (5.000 = 5%).
        rate_percent=rule.rate_percent,
        # O valor da energia solar compensada (Green) fica fora da base do imposto.
        exclude_compensated_energy=rule.exclude_compensated_energy,
        # Onde a regra vale e qual norma a fundamenta.
        jurisdiction=rule.jurisdiction,
        legal_basis=rule.legal_basis,
    )

# Sessão de recarga do banco -  SessionInput, a "ficha" da recarga que o motor usa para calcular a cobrança.
def session_to_input(session: ChargingSession) -> SessionInput:
    return SessionInput(
        session_id=session.id,
        user_id=session.user_id,
        # Horários: início, desconexão do carro e fim do fluxo de energia (a ociosidade conta a partir dele).
        started_at=session.started_at,
        ended_at=session.ended_at,
        energy_ended_at=session.energy_ended_at,
        # Energia medida: total, parte solar (Green) e parte da rede (Grid).
        total_kwh=session.total_kwh,
        green_kwh=session.green_kwh,
        grid_kwh=session.grid_kwh,
        # Como a sessão terminou (define a regra de cobrança) e se ela já foi aprovada para entrar na fatura.
        end_status=session.end_status,
        validation_status=session.validation_status,
        # A potência dele serve para recusar energia impossível (mais kWh do que o carregador consegue entregar).
        charger_rated_power_kw=session.charger.rated_power_kw,
        # Código do erro, quando a sessão foi interrompida por falha do sistema.
        failure_code=session.failure_code,
        # Se se o fim da energia não vier informado para descobrir quando ela parou
        power_samples=tuple(PowerSample(s.measured_at, s.power_kw, s.green_power_kw) for s in session.samples),
    )
