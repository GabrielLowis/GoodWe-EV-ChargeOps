## Motor de rateio do EV ChargeOps (Frente 3).

"""Uso típico (o serviço de faturamento faz isso a partir do banco):

    from backend.rateio import calculate_session, summarize_invoice
    charge = calculate_session(sessao, tarifa, impostos, feriados, fuso)
    print(charge.total, charge.calculation["explanation"])
"""

# Este arquivo é a "porta de entrada" do pacote rateio. Ele reúne as funções e estruturas principais,
# para quem usa o motor importar tudo de um lugar só ("from backend.rateio import calculate_session"),
# sem precisar saber em qual arquivo cada coisa mora.
#
# Mapa do pacote:
#   money.py      -> contas com dinheiro e energia (Decimal, arredondamento, formatação em reais)
#   models.py     -> as "fichas" que entram e saem do motor (tarifa, sessão, resultado...)
#   bands.py      -> em qual faixa horária cai cada momento e divisão da sessão em trechos
#   allocation.py -> quantos kWh foram consumidos em cada trecho
#   idle.py       -> minutos de ociosidade (vaga ocupada depois do fim da carga)
#   engine.py     -> junta tudo: calcula a sessão e monta a memória de cálculo

from backend.rateio.engine import ENGINE_VERSION, calculate_session, check_billable, summarize_invoice
from backend.rateio.models import (
    BandPrice,
    InvalidTariffError,
    InvoiceTotals,
    PowerSample,
    SessionCharge,
    SessionInput,
    SessionNotBillableError,
    TariffSpec,
    TaxRuleSpec,
    TimeWindow,
)

# __all__ é a lista oficial do que o pacote oferece para fora. Ela também avisa ao ruff que os imports acima são usados de propósito (para serem reaproveitados por quem importa o pacote).
__all__ = [
    "ENGINE_VERSION",
    "BandPrice",
    "InvalidTariffError",
    "InvoiceTotals",
    "PowerSample",
    "SessionCharge",
    "SessionInput",
    "SessionNotBillableError",
    "TariffSpec",
    "TaxRuleSpec",
    "TimeWindow",
    "calculate_session",
    "check_billable",
    "summarize_invoice",
]
