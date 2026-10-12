## Motor de rateio do EV ChargeOps (modelo híbrido definido na Sprint 1). ##

"""     Fórmula por sessão:

    Energia Green  = soma( kWh Green do trecho x preço Green da faixa do trecho )
    Energia Grid   = soma( kWh Grid do trecho  x preço Grid da faixa do trecho )
    Ociosidade     = minutos após o fim da energia, menos 15 de tolerância, x taxa/min
    Subtotal       = Green + Grid + Ociosidade
    Imposto        = subtotal x alíquota (uma linha por imposto vigente)
    Overhead       = subtotal x percentual do condomínio (pode ser 0%)
    Total          = Subtotal + Imposto + Overhead

A fatura mensal é a soma das sessões válidas do morador. Cada parcela é
arredondada ao centavo por sessão, de modo que a soma das linhas feche
exatamente com o total da fatura.
"""

# Este é o arquivo principal do motor. Ele junta as outras peças do pacote:
#   bands.py (divide a sessão em trechos de faixa) -> allocation.py (quantos kWh em cada trecho)
#   -> idle.py (minutos de ociosidade) -> preços da tarifa -> impostos e overhead -> memória de cálculo.
# Função principal: calculate_session. Ela recebe fichas simples (models.py) e não sabe nada de banco.

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from backend.db.enums import BAND_LABELS_PT, ChargeRule, SessionEndStatus, ValidationStatus
from backend.rateio.allocation import (
    METHOD_DESCRIPTIONS,
    METHOD_POWER_CURVE,
    allocation_weights,
    split_quantity,
)
from backend.rateio.bands import day_type_label, split_by_band
from backend.rateio.idle import ENERGY_END_SOURCE_LABELS, IdleResult, compute_idle
from backend.rateio.models import (
    HolidaySet,
    InvoiceTotals,
    SessionCharge,
    SessionInput,
    SessionNotBillableError,
    TariffSpec,
    TaxRuleSpec,
)
from backend.rateio.money import ZERO, brl, dec_str, kwh, money, pt_number, seconds_between

# Versão do motor, gravada em cada fatura. Se a regra de cálculo mudar um dia, dá para saber qual versão calculou cada conta antiga.
ENGINE_VERSION = "1.0.0"

# Diferença aceitável entre Green + Grid e o total medido (arredondamento da SEMS).
ENERGY_BALANCE_TOLERANCE_KWH = Decimal("0.05")

# Margem sobre potência nominal x tempo antes de considerar a energia impossível.
PHYSICAL_MARGIN = Decimal("1.05")

# Texto de cada regra de cobrança, que aparece na memória de cálculo (casos da Sprint 1).
RULE_DESCRIPTIONS = {
    ChargeRule.NORMAL: (
        "Sessão concluída normalmente: cobra-se a energia (Green + Grid) e a ociosidade após a tolerância."
    ),
    ChargeRule.USER_STOPPED_NO_IDLE: (
        "Sessão encerrada pelo morador antes do término: cobra-se apenas a energia entregue; "
        "a taxa de ociosidade não se aplica a sessões interrompidas (Sprint 1, seção 6.4)."
    ),
    ChargeRule.SYSTEM_FAILURE_NO_CHARGE: (
        "Sessão interrompida por falha do sistema: fica registrada para auditoria e não gera "
        "cobrança (Sprint 1, seção 6.4)."
    ),
}

# Nome de cada imposto para os textos da memória de cálculo.
TAX_LABELS = {"icms": "ICMS", "iss": "ISS", "ibs": "IBS", "cbs": "CBS"}



# Validações antes de cobrar

# Converte a classificação de encerramento (etapa 4 do fluxo) em regra de cobrança.
def charge_rule_for(end_status: str) -> ChargeRule:
    rules = {
        SessionEndStatus.COMPLETED: ChargeRule.NORMAL,
        SessionEndStatus.USER_STOPPED: ChargeRule.USER_STOPPED_NO_IDLE,
        SessionEndStatus.SYSTEM_FAILURE: ChargeRule.SYSTEM_FAILURE_NO_CHARGE,
    }
    try:
        return rules[SessionEndStatus(end_status)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Status de encerramento sem regra de cobrança: {end_status!r}") from exc

# Defesa em profundidade: o motor recusa sessões que não deveriam chegar até ele.
def check_billable(session: SessionInput) -> None:
    sid = session.session_id
    for moment in (session.started_at, session.ended_at, session.energy_ended_at):
        if moment is not None and moment.tzinfo is None:
            raise SessionNotBillableError(
                sid, "naive_datetime", "data sem fuso horário (informe o offset, ex.: -03:00)"
            )
    
    # Precisa ter morador, estar aprovada, ter terminado e terminar depois de começar.
    if session.user_id is None:
        raise SessionNotBillableError(sid, "unattributed", "sessão sem morador atribuído")
    if session.validation_status != ValidationStatus.APPROVED:
        raise SessionNotBillableError(
            sid,
            "not_approved",
            f"sessão com validação '{session.validation_status}': só sessões aprovadas entram na fatura",
        )
    if session.end_status == SessionEndStatus.IN_PROGRESS or session.ended_at is None:
        raise SessionNotBillableError(sid, "in_progress", "sessão ainda em andamento")
    if session.ended_at < session.started_at:
        raise SessionNotBillableError(sid, "time_order", "fim anterior ao início")
    if session.end_status == SessionEndStatus.SYSTEM_FAILURE:
        return  # não será cobrada: dispensa as verificações de energia

    # Energia não pode ser negativa.
    if min(session.total_kwh, session.green_kwh, session.grid_kwh) < 0:
        raise SessionNotBillableError(sid, "negative_energy", "energia negativa")
    gap = abs(session.green_kwh + session.grid_kwh - session.total_kwh)
    if gap > ENERGY_BALANCE_TOLERANCE_KWH:
        raise SessionNotBillableError(
            sid,
            "energy_balance",
            f"Green ({session.green_kwh}) + Grid ({session.grid_kwh}) difere do total ({session.total_kwh}) "
            f"em {gap} kWh",
        )
    
    # Regra física: o carregador não entrega mais do que potência x tempo (com a margem de 5%).
    hours = seconds_between(session.started_at, session.ended_at) / Decimal(3600)
    max_possible = session.charger_rated_power_kw * hours * PHYSICAL_MARGIN
    if session.total_kwh > max_possible + ENERGY_BALANCE_TOLERANCE_KWH:
        raise SessionNotBillableError(
            sid,
            "physically_impossible",
            f"{session.total_kwh} kWh em {pt_number(hours, 2)} h excede o máximo físico de "
            f"{pt_number(max_possible, 2)} kWh para {session.charger_rated_power_kw} kW",
        )



# Cálculo de uma sessão

# A função principal do motor, em 8 passos numerados (os mesmos da documentação).
def calculate_session(
    session: SessionInput,
    tariff: TariffSpec,
    tax_rules: Sequence[TaxRuleSpec],
    holidays: HolidaySet,
    tz: ZoneInfo,
) -> SessionCharge:
    # Calcula as cinco parcelas de uma sessão e monta a memória de cálculo.
    # 1. Recusa o que não pode ser cobrado (defesa em profundidade).
    check_billable(session)
    tariff.validate()

    # 2. Regra de cobrança pelo tipo de encerramento (casos excepcionais da Sprint 1).
    rule = charge_rule_for(session.end_status)

    # 3. Fim do fluxo de energia: informado, estimado pela curva ou desconhecido.
    idle = compute_idle(session, tariff.idle_tolerance_minutes)

    if rule == ChargeRule.SYSTEM_FAILURE_NO_CHARGE:
        return _failure_charge(session, tariff, idle, tz)

    # 4. Divide o intervalo de carga (início -> fim da energia) em trechos de faixa.
    assert session.ended_at is not None  # garantido por check_billable
    charging_end = idle.energy_end or session.ended_at
    segments = split_by_band(session.started_at, charging_end, tariff, holidays, tz)

    # 5. Distribui os kWh medidos entre os trechos (curva de potência ou tempo).
    green_weights, grid_weights, method = allocation_weights(
        segments, session.power_samples, session.started_at, charging_end
    )
    green_parts = split_quantity(kwh(session.green_kwh), green_weights)
    grid_parts = split_quantity(kwh(session.grid_kwh), grid_weights)

    # 6. Valoriza cada trecho com o preço Green/Grid da sua faixa.
    segment_rows: list[dict[str, Any]] = []
    explanation: list[str] = []
    green_value = grid_value = ZERO
    for index, (segment, green_kwh, grid_kwh) in enumerate(
        zip(segments, green_parts, grid_parts, strict=True), start=1
    ):
        price = tariff.price(segment.band)
        seg_green = green_kwh * price.green_price_per_kwh
        seg_grid = grid_kwh * price.grid_price_per_kwh
        green_value += seg_green
        grid_value += seg_grid
        start_local, end_local = segment.start.astimezone(tz), segment.end.astimezone(tz)
        minutes = seconds_between(segment.start, segment.end) / Decimal(60)
        segment_rows.append(
            {
                "index": index,
                "start": start_local.isoformat(),
                "end": end_local.isoformat(),
                "minutes": dec_str(minutes, 1),
                "band": str(segment.band),
                "band_label": BAND_LABELS_PT[segment.band],
                "day_type": day_type_label(start_local.date(), holidays),
                "green_kwh": dec_str(green_kwh, 3),
                "grid_kwh": dec_str(grid_kwh, 3),
                "green_price_per_kwh": dec_str(price.green_price_per_kwh, 4),
                "grid_price_per_kwh": dec_str(price.grid_price_per_kwh, 4),
                "green_value": dec_str(seg_green, 6),
                "grid_value": dec_str(seg_grid, 6),
            }
        )
        explanation.append(
            f"Trecho {index}: {start_local:%d/%m %H:%M}-{end_local:%H:%M} "
            f"({BAND_LABELS_PT[segment.band]}, {day_type_label(start_local.date(), holidays)}): "
            f"{pt_number(green_kwh, 3)} kWh Green x {brl(price.green_price_per_kwh, 4)} + "
            f"{pt_number(grid_kwh, 3)} kWh Grid x {brl(price.grid_price_per_kwh, 4)} = "
            f"{brl(seg_green + seg_grid, 4)}"
        )

    # Só agora arredonda ao centavo: a soma dos trechos é feita com todas as casas.
    green_amount = money(green_value)
    grid_amount = money(grid_value)

    # 7. Ociosidade (somente sessão concluída normalmente), subtotal, impostos e overhead.
    idle_applies = rule == ChargeRule.NORMAL
    idle_minutes = idle.billable_minutes if idle_applies else 0
    idle_amount = money(Decimal(idle_minutes) * tariff.idle_fee_per_minute)

    subtotal = green_amount + grid_amount + idle_amount
    tax_rows, tax_amount = _taxes(subtotal, green_amount, tax_rules)
    overhead_amount = money(subtotal * tariff.overhead_percent / Decimal(100))
    total = subtotal + tax_amount + overhead_amount

    # extend acrescenta várias frases de uma vez no fim da explicação.
    explanation.extend(
        _summary_lines(
            green_amount,
            grid_amount,
            idle,
            idle_applies,
            idle_minutes,
            idle_amount,
            tariff,
            subtotal,
            tax_rows,
            overhead_amount,
            total,
        )
    )

    # 8. Memória de cálculo: tudo o que é preciso para refazer a conta.
    notes: list[str] = []
    gap = session.green_kwh + session.grid_kwh - session.total_kwh
    if gap != 0:
        notes.append(
            f"Green + Grid difere do total medido em {pt_number(gap, 3)} kWh (arredondamento da fonte); "
            "cobram-se os campos Green e Grid, como definido na Sprint 1."
        )
    if method != METHOD_POWER_CURVE and len(segments) > 1:
        notes.append("Sessão atravessou faixas sem curva de potência: divisão estimada pelo tempo.")

    # O dicionário que vira o JSON guardado no item da fatura (coluna calculation).
    calculation = {
        "engine_version": ENGINE_VERSION,
        "session": _session_block(session, idle, tz),
        "rule": {"code": str(rule), "description": RULE_DESCRIPTIONS[rule]},
        "tariff": tariff.snapshot(tz),
        "band_split": {
            "method": method,
            "method_description": METHOD_DESCRIPTIONS[method],
            "segments": segment_rows,
        },
        "components": {
            "green": {
                "label": "Energia verde (solar/bateria)",
                "kwh": dec_str(kwh(session.green_kwh), 3),
                "unrounded": dec_str(green_value, 6),
                "amount": dec_str(green_amount, 2),
                "formula": "soma(kWh Green do trecho x preço Green da faixa), arredondada ao centavo",
            },
            "grid": {
                "label": "Energia da rede",
                "kwh": dec_str(kwh(session.grid_kwh), 3),
                "unrounded": dec_str(grid_value, 6),
                "amount": dec_str(grid_amount, 2),
                "formula": "soma(kWh Grid do trecho x preço Grid da faixa), arredondada ao centavo",
            },
            "idle": _idle_block(idle, idle_applies, idle_minutes, idle_amount, tariff),
            "subtotal": {"amount": dec_str(subtotal, 2), "formula": "Green + Grid + Ociosidade"},
            "taxes": tax_rows,
            "tax_total": dec_str(tax_amount, 2),
            "overhead": {
                "label": "Overhead operacional",
                "percent": dec_str(tariff.overhead_percent, 2),
                "base": dec_str(subtotal, 2),
                "amount": dec_str(overhead_amount, 2),
                "formula": "subtotal x percentual definido pela assembleia",
            },
            "total": dec_str(total, 2),
        },
        "explanation": explanation,
        "notes": notes,
    }

    # O resultado final: os valores (que viram colunas do item da fatura) e a memória de cálculo.
    return SessionCharge(
        session_id=session.session_id,
        charge_rule=str(rule),
        green_kwh=kwh(session.green_kwh),
        grid_kwh=kwh(session.grid_kwh),
        idle_minutes=idle_minutes,
        green_amount=green_amount,
        grid_amount=grid_amount,
        idle_amount=idle_amount,
        subtotal=subtotal,
        tax_amount=tax_amount,
        overhead_amount=overhead_amount,
        total=total,
        tariff_id=tariff.id,
        # Os ids dos impostos usados (só os que têm id; os criados em teste podem não ter).
        tax_rule_ids=tuple(r.id for r in tax_rules if r.id is not None),
        calculation=calculation,
    )


# Impostos: uma linha para cada imposto que vale. A base é o subtotal, menos a energia solar quando a regra mandar excluir. 
def _taxes(
    subtotal: Decimal, green_amount: Decimal, tax_rules: Sequence[TaxRuleSpec]
) -> tuple[list[dict[str, Any]], Decimal]:
    """Uma linha por imposto vigente; a base exclui a energia compensada quando a regra permitir."""
    rows: list[dict[str, Any]] = []
    total = money(ZERO)
    for rule in tax_rules:
        excluded = green_amount if rule.exclude_compensated_energy else ZERO
        base = subtotal - excluded
        amount = money(base * rule.rate_percent / Decimal(100))
        total += amount
        rows.append(
            {
                "rule_id": rule.id,
                "tax_type": rule.tax_type,
                "label": TAX_LABELS.get(rule.tax_type, rule.tax_type.upper()),
                "rate_percent": dec_str(rule.rate_percent, 3),
                "exclude_compensated_energy": rule.exclude_compensated_energy,
                "excluded_from_base": dec_str(excluded, 2),
                "base": dec_str(base, 2),
                "amount": dec_str(amount, 2),
                "legal_basis": rule.legal_basis,
            }
        )
    return rows, total

# Parte "session" da memória de cálculo: os dados da recarga, com os horários no fuso do condomínio.
def _session_block(session: SessionInput, idle: IdleResult, tz: ZoneInfo) -> dict[str, Any]:
    def local(moment: datetime | None) -> str | None:
        return moment.astimezone(tz).isoformat() if moment else None

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "started_at": local(session.started_at),
        "energy_ended_at": local(idle.energy_end),
        "energy_end_source": idle.energy_end_source,
        "ended_at": local(session.ended_at),
        "end_status": session.end_status,
        "failure_code": session.failure_code,
        "total_kwh": dec_str(kwh(session.total_kwh), 3),
        "green_kwh": dec_str(kwh(session.green_kwh), 3),
        "grid_kwh": dec_str(kwh(session.grid_kwh), 3),
        "charger_rated_power_kw": dec_str(session.charger_rated_power_kw, 2),
        "power_samples": len(session.power_samples),
    }

# Parte "idle" da memória de cálculo: de onde veio o fim da energia, minutos, tolerância e valor.
def _idle_block(idle: IdleResult, applies: bool, minutes: int, amount: Decimal, tariff: TariffSpec) -> dict[str, Any]:
    return {
        "label": "Ociosidade (vaga ocupada após o fim da carga)",
        "applies": applies,
        "energy_end_source": idle.energy_end_source,
        "energy_end_source_label": ENERGY_END_SOURCE_LABELS[idle.energy_end_source],
        "minutes_after_energy_end": idle.minutes_after_energy_end,
        "tolerance_minutes": idle.tolerance_minutes,
        "billable_minutes": minutes,
        "fee_per_minute": dec_str(tariff.idle_fee_per_minute, 4),
        "amount": dec_str(amount, 2),
        "formula": "max(0, minutos completos após o fim da energia - tolerância) x taxa por minuto",
    }

# As frases finais da explicação: energia, ociosidade (três casos), subtotal, cada imposto, overhead e total.
def _summary_lines(
    green_amount: Decimal,
    grid_amount: Decimal,
    idle: IdleResult,
    idle_applies: bool,
    idle_minutes: int,
    idle_amount: Decimal,
    tariff: TariffSpec,
    subtotal: Decimal,
    tax_rows: list[dict[str, Any]],
    overhead_amount: Decimal,
    total: Decimal,
) -> list[str]:
    lines = [
        f"Energia verde (solar/bateria): {brl(green_amount)}",
        f"Energia da rede: {brl(grid_amount)}",
    ]
    if not idle_applies:
        lines.append("Ociosidade: não se aplica a esta sessão (encerrada antes do término).")
    elif idle.energy_end is None:
        lines.append("Ociosidade: fim do fluxo de energia desconhecido, nada cobrado.")
    else:
        lines.append(
            f"Ociosidade: {idle.minutes_after_energy_end} min após o fim da carga - "
            f"{idle.tolerance_minutes} min de tolerância = {idle_minutes} min x "
            f"{brl(tariff.idle_fee_per_minute, 4)} = {brl(idle_amount)}"
        )
    lines.append(f"Subtotal: {brl(subtotal)}")
    for row in tax_rows:
        extra = " (energia compensada excluída da base)" if row["exclude_compensated_energy"] else ""
        lines.append(
            f"{row['label']} {pt_number(Decimal(row['rate_percent']), 3)}% sobre "
            f"{brl(Decimal(row['base']))}{extra}: {brl(Decimal(row['amount']))}"
        )
    lines.append(
        f"Overhead operacional {pt_number(tariff.overhead_percent, 2)}% sobre o subtotal: {brl(overhead_amount)}"
    )
    lines.append(f"Total da sessão: {brl(total)}")
    return lines

# Caminho da falha do sistema: a sessão aparece na fatura com todos os valores em zero, com o motivo e a energia que foi entregue mas não cobrada. O morador não paga por algo que não dependeu dele.
def _failure_charge(session: SessionInput, tariff: TariffSpec, idle: IdleResult, tz: ZoneInfo) -> SessionCharge:
    # Sessão interrompida por falha do sistema: linha com valor zero e o motivo.
    zero = money(ZERO)
    reason = f"código {session.failure_code}" if session.failure_code else "sem código informado"
    calculation = {
        "engine_version": ENGINE_VERSION,
        "session": _session_block(session, idle, tz),
        "rule": {
            "code": str(ChargeRule.SYSTEM_FAILURE_NO_CHARGE),
            "description": RULE_DESCRIPTIONS[ChargeRule.SYSTEM_FAILURE_NO_CHARGE],
        },
        "tariff": tariff.snapshot(tz),
        "band_split": {"method": None, "segments": []},
        "components": {
            "green": {
                "kwh": "0.000",
                "amount": "0.00",
                "delivered_not_charged_kwh": dec_str(kwh(session.green_kwh), 3),
            },
            "grid": {"kwh": "0.000", "amount": "0.00", "delivered_not_charged_kwh": dec_str(kwh(session.grid_kwh), 3)},
            "idle": {"applies": False, "billable_minutes": 0, "amount": "0.00"},
            "subtotal": {"amount": "0.00"},
            "taxes": [],
            "tax_total": "0.00",
            "overhead": {"percent": dec_str(tariff.overhead_percent, 2), "amount": "0.00"},
            "total": "0.00",
        },
        "explanation": [
            f"Sessão interrompida por falha do sistema ({reason}).",
            f"Energia entregue até a falha: {pt_number(kwh(session.total_kwh), 3)} kWh, não cobrada.",
            "O morador não é penalizado por algo que não dependeu dele. Total da sessão: R$ 0,00",
        ],
        "notes": [],
    }
    return SessionCharge(
        session_id=session.session_id,
        charge_rule=str(ChargeRule.SYSTEM_FAILURE_NO_CHARGE),
        green_kwh=kwh(0),
        grid_kwh=kwh(0),
        idle_minutes=0,
        green_amount=zero,
        grid_amount=zero,
        idle_amount=zero,
        subtotal=zero,
        tax_amount=zero,
        overhead_amount=zero,
        total=zero,
        tariff_id=tariff.id,
        tax_rule_ids=(),
        calculation=calculation,
    )



# Fatura mensal

# Soma as sessões do mês. As somas começam em money(ZERO) e kwh(0) para o resultado ser sempre Decimal, mesmo sem nenhuma sessão (fatura zero).
def summarize_invoice(charges: Sequence[SessionCharge]) -> InvoiceTotals:
   # Soma as parcelas das sessões. Sem sessões, a fatura é zero (sem mensalidade mínima).
   
    # Função auxiliar: soma um campo de todas as sessões. getattr(c, "total") é o mesmo que c.total.
    def total_of(attr: str) -> Decimal:
        return sum((getattr(c, attr) for c in charges), money(ZERO))

    return InvoiceTotals(
        sessions_count=len(charges),
        green_kwh=sum((c.green_kwh for c in charges), kwh(0)),
        grid_kwh=sum((c.grid_kwh for c in charges), kwh(0)),
        idle_minutes=sum(c.idle_minutes for c in charges),
        green_amount=total_of("green_amount"),
        grid_amount=total_of("grid_amount"),
        idle_amount=total_of("idle_amount"),
        subtotal=total_of("subtotal"),
        tax_amount=total_of("tax_amount"),
        overhead_amount=total_of("overhead_amount"),
        total=total_of("total"),
    )
