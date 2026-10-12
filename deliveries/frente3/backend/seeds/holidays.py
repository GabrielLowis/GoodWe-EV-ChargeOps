"""Feriados nacionais em que todas as horas são fora de ponta (lista da ANEEL).

Fonte: ANEEL, "Postos tarifários" (gov.br/aneel). Os postos tarifários valem
só em dias úteis; sábados, domingos e os 11 feriados abaixo são fora de ponta.
Feriados locais podem ser cadastrados pelo síndico na tabela holidays.
"""

from __future__ import annotations

from datetime import date, timedelta

# Calcula o domingo de Páscoa de qualquer ano.
def easter_sunday(year: int) -> date:
    """Domingo de Páscoa (algoritmo gregoriano anônimo, Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 (nome do algoritmo original)
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)

# Os 11 feriados nacionais de um ano, como um dicionário data -> nome.
def aneel_national_holidays(year: int) -> dict[date, str]:
    easter = easter_sunday(year)
    return {
        date(year, 1, 1): "Confraternização Universal",
        easter - timedelta(days=47): "Terça-feira de Carnaval",
        easter - timedelta(days=2): "Sexta-feira da Paixão",
        date(year, 4, 21): "Tiradentes",
        date(year, 5, 1): "Dia do Trabalhador",
        easter + timedelta(days=60): "Corpus Christi",
        date(year, 9, 7): "Independência do Brasil",
        date(year, 10, 12): "Nossa Senhora Aparecida",
        date(year, 11, 2): "Finados",
        date(year, 11, 15): "Proclamação da República",
        date(year, 12, 25): "Natal",
    }
