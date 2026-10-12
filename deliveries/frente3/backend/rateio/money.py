"""Aritmética de dinheiro e energia com Decimal.

Nunca usamos float para valores financeiros: 0.1 + 0.2 em float dá
0.30000000000000004. Decimal faz a conta em base 10, como a calculadora.
"""
# Ferramentas pequenas usadas por todo o motor: arredondar dinheiro e energia, medir tempo e escrever números no formato brasileiro.

# UTC é o fuso "zero", usado para medir tempo sem confusão de fuso.
from datetime import UTC, datetime

# ROUND_HALF_UP = arredondar "meio para cima", como na escola (0,5 sobe).
from decimal import ROUND_HALF_UP, Decimal

# Decimal sempre criado a partir de TEXTO ("0.01"), nunca de float: Decimal(0.01) carregaria o erro do
# float e viraria 0.01000000000000000020816681711721685...
CENT = Decimal("0.01")  # centavo
KWH_QUANTUM = Decimal("0.001")  # 1 Wh: resolução da energia gravada no banco
ZERO = Decimal("0")


# Aceita número em qualquer formato e devolve Decimal.
def to_decimal(value: object) -> Decimal:
    """Converte int, str, float ou Decimal para Decimal sem ruído binário."""
    if isinstance(value, Decimal):
        return value  # já é Decimal: devolve como está
    if isinstance(value, float):
        # Passa pelo texto primeiro: str(0.1) é "0.1", e Decimal("0.1") é exato.
        return Decimal(str(value))
    # int ou texto. O comentário no fim da linha só avisa o verificador de tipos de que é intencional.
    return Decimal(value)  # type: ignore[arg-type]


# Arredonda para centavos. O round() do Python usaria o "arredondamento bancário" (round(2.5) dá 2), por isso o motor usa quantize com ROUND_HALF_UP.
def money(value: Decimal) -> Decimal:
    """Arredonda para centavos, meio para cima (R$ 1,005 -> R$ 1,01)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# Arredonda energia para 3 casas (1 Wh), o mesmo formato da coluna do banco.
def kwh(value: object) -> Decimal:
    """Normaliza energia para 3 casas (Wh), como na coluna NUMERIC(10,3)."""
    return to_decimal(value).quantize(KWH_QUANTUM, rounding=ROUND_HALF_UP)


# Quantos segundos se passaram entre dois instantes. Os dois são convertidos para UTC antes da subtração,
# para a conta ficar certa mesmo que os horários venham com fusos diferentes ou atravessem um horário de verão.
def seconds_between(start: datetime, end: datetime) -> Decimal:
    """Segundos entre dois instantes (convertendo para UTC, à prova de horário de verão)."""
    delta = end.astimezone(UTC) - start.astimezone(UTC)
    return Decimal(str(delta.total_seconds()))


# Formatação para a memória de cálculo 

# Decimal -> texto com um número fixo de casas. Decimal(1).scaleb(-places) é 10 elevado a -places (places=2 dá 0.01), ou seja, o "tamanho do degrau" do arredondamento.
def dec_str(value: Decimal, places: int) -> str:
    """Decimal -> texto com casas fixas (JSON guarda número como texto para não perder precisão)."""
    return str(value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


# Número no jeito brasileiro. O f-string com ":,.2f" escreve no jeito americano (1,234.50); depois, três trocas: vírgula vira "_" (provisório), ponto vira vírgula e "_" vira ponto -> 1.234,50.
def pt_number(value: Decimal, places: int) -> str:
    """Formato brasileiro: 1234.5 -> '1.234,50'."""
    text = f"{value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP):,.{places}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


# Valor em reais para os textos da memória de cálculo: brl(Decimal("43.5")) -> "R$ 43,50".
def brl(value: Decimal, places: int = 2) -> str:
    return f"R$ {pt_number(value, places)}"

