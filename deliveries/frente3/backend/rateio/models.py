## Estruturas de entrada e saída do motor de rateio. ##

""" O motor não conhece banco de dados nem HTTP: recebe estes objetos simples e
devolve o cálculo. Isso permite testar toda a regra financeira sem PostgreSQL
e reaproveitar o motor em qualquer ponto do backend (Frente 2).
"""

# Como ler este arquivo: quase tudo aqui é uma "ficha" com campos, criada com @dataclass.
# - @dataclass monta sozinho o construtor da classe a partir dos campos listados
#   (BandPrice(Decimal("0.30"), Decimal("1.45")) já funciona, sem escrever um __init__).
# - frozen=True deixa a ficha imutável: depois de criada, nenhum campo pode ser trocado (daria erro).
#   Assim o cálculo nunca altera sem querer os dados que recebeu.
# - Campos com "= valor" têm valor padrão e podem ser omitidos; os sem padrão são obrigatórios e vêm antes.

from __future__ import annotations

# Mapping: "um dicionário", usado só como tipo.
from collections.abc import Mapping
from dataclasses import dataclass, field

# tzinfo: o tipo de um fuso horário (ZoneInfo é um tzinfo).
from datetime import date, datetime, time, tzinfo
from decimal import Decimal
from itertools import pairwise
from typing import Any

from backend.db.enums import Band
from backend.rateio.money import dec_str


# Erros próprios do motor
# Erro lançado quando uma sessão não pode ser cobrada. Além da mensagem, guarda um "code" curto
# (ex.: "not_approved", "physically_impossible"), que o service.py grava na fatura e na auditoria.
class SessionNotBillableError(ValueError):
    # A sessão não pode ser faturada (ex.: não aprovada, sem morador, energia impossível).

    def __init__(self, session_id: object, code: str, message: str) -> None:
        # super() chama o construtor da classe-mãe (ValueError) com a mensagem completa.
        super().__init__(f"Sessão {session_id}: {message}")
        self.session_id = session_id
        self.code = code


# Erro de configuração da tabela tarifária (pego antes de calcular qualquer sessão).
class InvalidTariffError(ValueError):
    """ Tabela tarifária mal configurada (ex.: janelas sobrepostas, faixa sem preço)."""



# Parâmetros de cobrança

# Os dois preços de uma faixa: kWh solar e kWh da rede.
@dataclass(frozen=True)
class BandPrice:
   # Preço por kWh de uma faixa, separado por origem da energia.

    green_price_per_kwh: Decimal
    grid_price_per_kwh: Decimal


# Uma janela de dia útil, ex.: TimeWindow(Band.PEAK, time(18, 0), time(21, 0)) = ponta das 18h às 21h.
@dataclass(frozen=True)
class TimeWindow:
    # Janela de dia útil (horário local) em que vale uma faixa diferente de fora de ponta.
    band: Band
    start: time
    end: time


# A tabela tarifária no formato do motor (o mappers.py monta esta ficha a partir do banco).
@dataclass(frozen=True)
class TariffSpec:

    name: str
    prices: Mapping[Band, BandPrice]  # dicionário faixa -> preços
    windows: tuple[TimeWindow, ...]  # tupla com quantas janelas houver
    idle_tolerance_minutes: int = 15
    idle_fee_per_minute: Decimal = Decimal("0")
    overhead_percent: Decimal = Decimal("0")
    weekends_holidays_off_peak: bool = True
    id: int | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    assembly_reference: str | None = None

    # Preço de uma faixa. Se a faixa não tiver preço, troca o KeyError do dicionário por um erro
    # mais claro. O "from exc" guarda o erro original junto, para facilitar a investigação.
    def price(self, band: Band) -> BandPrice:
        try:
            return self.prices[band]
        except KeyError as exc:
            raise InvalidTariffError(f"Tarifa '{self.name}' não define preço para a faixa {band}") from exc

    # Confere a tabela antes de usar: existe preço fora de ponta; cada janela termina depois de começar
    # (não atravessa a meia-noite), não é fora de ponta e tem preço; janelas vizinhas não se sobrepõem.
    def validate(self) -> None:
        """Confere se a tabela é utilizável antes de calcular qualquer sessão."""
        if Band.OFF_PEAK not in self.prices:
            raise InvalidTariffError(f"Tarifa '{self.name}' precisa do preço fora de ponta (faixa padrão)")
        # sorted(..., key=...) ordena as janelas pelo horário de início.
        ordered = sorted(self.windows, key=lambda w: w.start)
        for window in ordered:
            if window.end <= window.start:
                raise InvalidTariffError(
                    f"Janela {window.start}-{window.end} inválida: janelas não atravessam a meia-noite"
                )
            if window.band == Band.OFF_PEAK:
                raise InvalidTariffError("Janelas servem para ponta/intermediário; o resto do dia já é fora de ponta")
            self.price(window.band)  # só para conferir que a faixa tem preço (dá erro se não tiver)
        # Compara cada janela com a seguinte: a próxima não pode começar antes de a anterior terminar.
        for previous, current in pairwise(ordered):
            if current.start < previous.end:
                raise InvalidTariffError(
                    f"Janelas sobrepostas: {previous.start}-{previous.end} e {current.start}-{current.end}"
                )

    # Cópia da tarifa que vai para a memória de cálculo, para a conta poder ser refeita no futuro
    # mesmo que a tarifa mude.
    def snapshot(self, tz: tzinfo) -> dict[str, Any]:
        # Cópia dos parâmetros usados, gravada na memória de cálculo (reprodutibilidade). 

        # Função dentro da função: converte uma data para o fuso do condomínio (ou None se não houver).
        def local(moment: datetime | None) -> str | None:
            return moment.astimezone(tz).isoformat() if moment else None

        return {
            "id": self.id,
            "name": self.name,
            "valid_from": local(self.valid_from),
            "valid_to": local(self.valid_to),
            "assembly_reference": self.assembly_reference,
            # Um item por faixa, em ordem fixa (sorted), com os preços em texto de 4 casas.
            "prices": {
                str(band): {
                    "green_price_per_kwh": dec_str(price.green_price_per_kwh, 4),
                    "grid_price_per_kwh": dec_str(price.grid_price_per_kwh, 4),
                }
                for band, price in sorted(self.prices.items())
            },
            # strftime("%H:%M") escreve o horário como texto, ex.: "18:00".
            "weekday_windows": [
                {"band": str(w.band), "start": w.start.strftime("%H:%M"), "end": w.end.strftime("%H:%M")}
                for w in sorted(self.windows, key=lambda w: w.start)
            ],
            "weekends_holidays_off_peak": self.weekends_holidays_off_peak,
            "idle_tolerance_minutes": self.idle_tolerance_minutes,
            "idle_fee_per_minute": dec_str(self.idle_fee_per_minute, 4),
            "overhead_percent": dec_str(self.overhead_percent, 2),
        }


# Um imposto que vale para a sessão (o motor recebe uma lista deles).
@dataclass(frozen=True)
class TaxRuleSpec:
    # Imposto vigente (ICMS, ISS, IBS ou CBS), tratado como parâmetro e não como constante.

    tax_type: str
    rate_percent: Decimal
    exclude_compensated_energy: bool = False  # True = a energia solar (Green) fica fora da base
    id: int | None = None
    jurisdiction: str | None = None
    legal_basis: str | None = None



# Entrada: a sessão de recarga

# Um ponto da curva de potência: "às 18:05, o carregador entregava 6,9 kW".
@dataclass(frozen=True)
class PowerSample:
    # Ponto da curva de potência (kW) medido em um instante.

    measured_at: datetime
    power_kw: Decimal
    green_power_kw: Decimal | None = None  # parte solar da potência, quando a fonte informa


# A ficha da sessão que o motor recebe (montada pelo mappers.py a partir do banco).
@dataclass(frozen=True)
class SessionInput:
    # Sessão pronta para o faturamento (já normalizada, atribuída e validada).

    session_id: int | str
    user_id: int | None
    started_at: datetime
    # Fim da ocupação (desconexão)
    ended_at: datetime | None  
    # Fim do fluxo de energia (base da ociosidade)
    energy_ended_at: datetime | None  
    total_kwh: Decimal
    green_kwh: Decimal
    grid_kwh: Decimal
    # Como terminou (define a regra de cobrança)
    end_status: str  
    # Só "approved" pode ser cobrada
    validation_status: str  
    # Potência do carregador (para recusar energia impossível)
    charger_rated_power_kw: Decimal  
    failure_code: str | None = None
    # Tupla vazia = sem curva de potência
    power_samples: tuple[PowerSample, ...] = ()  



# Saída: o resultado do cálculo

# Um pedaço da sessão que cabe inteiro numa faixa (ex.: 18:00-20:30, ponta).
@dataclass(frozen=True)
class Segment:
   # Trecho da sessão dentro de uma única faixa horária.

    start: datetime
    end: datetime
    band: Band


# O que o motor devolve para uma sessão: os valores e a memória de cálculo.
@dataclass(frozen=True)
class SessionCharge:
    # Resultado do rateio de uma sessão: as cinco parcelas e a memória de cálculo.

    session_id: int | str
    charge_rule: str
    green_kwh: Decimal
    grid_kwh: Decimal
    idle_minutes: int
    green_amount: Decimal
    grid_amount: Decimal
    idle_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    overhead_amount: Decimal
    total: Decimal
    tariff_id: int | None
    tax_rule_ids: tuple[int, ...]
    # repr=False: não aparece quando o objeto é impresso (a memória de cálculo é enorme).
    calculation: dict[str, Any] = field(repr=False)


# A soma de todas as sessões do mês (o summarize_invoice do engine.py monta esta ficha).
@dataclass(frozen=True)
class InvoiceTotals:
    # Soma das parcelas de todas as sessões da fatura mensal.

    sessions_count: int
    green_kwh: Decimal
    grid_kwh: Decimal
    idle_minutes: int
    green_amount: Decimal
    grid_amount: Decimal
    idle_amount: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    overhead_amount: Decimal
    total: Decimal


# Apelido de tipo: HolidaySet é só um nome curto para "conjunto imutável de datas" (os feriados).
HolidaySet = frozenset[date]

