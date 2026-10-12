"""Feriados nacionais fora de ponta (lista da ANEEL) usados pelo seed."""

from datetime import date

from backend.seeds.holidays import aneel_national_holidays, easter_sunday

# A Páscoa de três anos, conferida no calendário. Se a receita da Páscoa tivesse um erro de conta, algum
# destes domingos sairia errado (e, com ele, o Carnaval, a Sexta-feira da Paixão e o Corpus Christi).
def test_pascoa_em_anos_conhecidos():
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert easter_sunday(2027) == date(2027, 3, 28)


# A lista de 2026 tem os 11 feriados, e os que dependem da Páscoa (05/04/2026) caem nos dias certos:
# Carnaval 47 dias antes (17/02), Sexta-feira da Paixão 2 dias antes (03/04) e Corpus Christi 60 dias
# depois (04/06). holidays[data] busca o nome do feriado; "data in holidays" pergunta se a data está na lista.
def test_lista_de_2026_tem_os_onze_feriados_da_aneel():
    holidays = aneel_national_holidays(2026)
    assert len(holidays) == 11
    assert holidays[date(2026, 2, 17)] == "Terça-feira de Carnaval"
    assert holidays[date(2026, 4, 3)] == "Sexta-feira da Paixão"
    assert holidays[date(2026, 6, 4)] == "Corpus Christi"
    assert date(2026, 9, 7) in holidays