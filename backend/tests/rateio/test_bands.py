## Classificação de faixas e divisão da sessão em trechos (sem banco). ##

# Como ler este arquivo:
# - band_at(momento, tarifa, feriados) diz em qual faixa cai um horário.
# - split_by_band(início, fim, tarifa, feriados, fuso) corta a sessão em trechos, cada um numa faixa só.
# - A tarifa de teste (fixture tariff) tem, nos dias úteis: intermediário 17h-18h, ponta 18h-21h e
#   intermediário 21h-22h; o resto do dia é fora de ponta. Sábado, domingo e feriado são fora de ponta
#   o dia todo.
# - Dias de setembro/2026 usados aqui: 07 (feriado, segunda), 19 (sábado), 20 (domingo), 21 (segunda),
#   25 (sexta) e 26 (sábado). at(21, 17, 30) = 21/09/2026 às 17:30.

from datetime import UTC, datetime, time
from decimal import Decimal

import pytest

from backend.db.enums import Band
from backend.rateio.bands import band_at, split_by_band
from backend.rateio.models import BandPrice, InvalidTariffError, TariffSpec, TimeWindow
from backend.tests.helpers import TZ, at, build_tariff

NO_HOLIDAYS: frozenset = frozenset()  # conjunto vazio: nenhum feriado


# Duração de um trecho em minutos. total_seconds() dá os segundos, e "// 60" divide descartando o resto.
def minutes(segment) -> int:
    return int((segment.end - segment.start).total_seconds() // 60)


# As bordas das janelas, minuto a minuto: 16:59 ainda é fora de ponta e 17:00 já é intermediário;
# 20:59 ainda é ponta e 21:00 já não é. O início da janela conta e o fim não.
# parametrize com três nomes: cada trio (hora, minuto, faixa esperada) é uma execução (9 no total).
# 21/09/2026 é uma segunda-feira (dia útil).
@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [
        (3, 0, Band.OFF_PEAK),
        (16, 59, Band.OFF_PEAK),
        (17, 0, Band.INTERMEDIATE),
        (17, 59, Band.INTERMEDIATE),
        (18, 0, Band.PEAK),
        (20, 59, Band.PEAK),
        (21, 0, Band.INTERMEDIATE),
        (21, 59, Band.INTERMEDIATE),
        (22, 0, Band.OFF_PEAK),
    ],
)
def test_faixa_em_dia_util(tariff, hour, minute, expected):
    assert band_at(at(21, hour, minute), tariff, NO_HOLIDAYS) == expected


# Sábado às 19h, que num dia útil seria ponta, é fora de ponta.
def test_fim_de_semana_e_fora_de_ponta_o_dia_todo(tariff):
    assert band_at(at(19, 19), tariff, NO_HOLIDAYS) == Band.OFF_PEAK  # sábado, 19h


# O mesmo horário (07/09 às 19h) com e sem o feriado na lista: fora de ponta no feriado, ponta sem ele.
# Isso mostra que a lista de feriados é o que faz a diferença.
def test_feriado_e_fora_de_ponta_o_dia_todo(tariff):
    independencia = frozenset({at(7, 0).date()})  # 07/09/2026, segunda-feira
    assert band_at(at(7, 19), tariff, independencia) == Band.OFF_PEAK
    assert band_at(at(7, 19), tariff, NO_HOLIDAYS) == Band.PEAK


# A regra do fim de semana é um parâmetro da tarifa, e não uma constante: se a assembleia desligar
# (weekends_holidays_off_peak=False), sábado às 19h passa a ser ponta.
def test_assembleia_pode_desligar_fora_de_ponta_no_fim_de_semana():
    tariff = build_tariff(weekends_holidays_off_peak=False)
    assert band_at(at(19, 19), tariff, NO_HOLIDAYS) == Band.PEAK


# O exemplo do plano: 17:30 às 20:30 vira dois trechos. .time() pega só o horário de cada data, para a
# comparação ficar fácil de ler.
def test_exemplo_do_plano_intermediario_e_ponta(tariff):
    """Plano da Sprint 2: 17:30-18:00 intermediário; 18:00-20:30 ponta."""
    segments = split_by_band(at(21, 17, 30), at(21, 20, 30), tariff, NO_HOLIDAYS, TZ)
    assert [(s.start.time(), s.end.time(), s.band) for s in segments] == [
        (time(17, 30), time(18, 0), Band.INTERMEDIATE),
        (time(18, 0), time(20, 30), Band.PEAK),
    ]


# Uma carga das 16h às 23h passa pelas cinco partes do dia útil, na ordem, com a duração de cada uma.
def test_noite_inteira_passa_pelas_cinco_janelas(tariff):
    segments = split_by_band(at(21, 16), at(21, 23), tariff, NO_HOLIDAYS, TZ)
    assert [(s.band, minutes(s)) for s in segments] == [
        (Band.OFF_PEAK, 60),
        (Band.INTERMEDIATE, 60),
        (Band.PEAK, 180),
        (Band.INTERMEDIATE, 60),
        (Band.OFF_PEAK, 60),
    ]


# Uma sessão que fica numa faixa só (10h às 12h) gera um trecho só, de 120 minutos.
def test_sessao_em_uma_so_faixa_gera_um_trecho(tariff):
    segments = split_by_band(at(21, 10), at(21, 12), tariff, NO_HOLIDAYS, TZ)
    assert [(s.band, minutes(s)) for s in segments] == [(Band.OFF_PEAK, 120)]


# Das 21:30 de sexta às 00:30 de sábado: 30 min de intermediário e, depois, um trecho fora de ponta que
# atravessa a meia-noite. As 2h de sexta (22h-24h) e a meia hora de sábado são unidas num trecho de 150 min.
def test_meia_noite_de_sexta_para_sabado_une_trechos_fora_de_ponta(tariff):
    # sexta 25/09 21:30 -> sábado 26/09 00:30
    segments = split_by_band(at(25, 21, 30), at(26, 0, 30), tariff, NO_HOLIDAYS, TZ)
    assert [(s.band, minutes(s)) for s in segments] == [(Band.INTERMEDIATE, 30), (Band.OFF_PEAK, 150)]


# Uma carga longa, do domingo à tarde até a segunda à noite. O primeiro trecho vai das 16h de domingo às
# 17h de segunda (8 h de domingo + 17 h de segunda, tudo fora de ponta); só depois vêm as janelas da segunda.
def test_domingo_para_segunda_muda_de_regra_a_meia_noite(tariff):
    # domingo 20/09 16:00 -> segunda 21/09 18:30: fim de semana todo fora de ponta,
    # segunda segue as janelas normais
    segments = split_by_band(at(20, 16), at(21, 18, 30), tariff, NO_HOLIDAYS, TZ)
    assert [(s.band, minutes(s)) for s in segments] == [
        (Band.OFF_PEAK, 8 * 60 + 17 * 60),  # 16h de domingo até 17h de segunda
        (Band.INTERMEDIATE, 60),
        (Band.PEAK, 30),
    ]


# A fonte de dados pode mandar os horários em UTC. O motor converte para o fuso do condomínio antes de
# decidir a faixa: 20:30 em UTC são 17:30 em São Paulo, que é intermediário. Sem a conversão, 20:30 seria
# lido como ponta.
def test_horarios_em_utc_sao_convertidos_para_o_fuso_do_condominio(tariff):
    # 20:30 UTC = 17:30 em São Paulo (UTC-3)
    start = datetime(2026, 9, 21, 20, 30, tzinfo=UTC)
    end = datetime(2026, 9, 21, 23, 30, tzinfo=UTC)
    segments = split_by_band(start, end, tariff, NO_HOLIDAYS, TZ)
    assert segments[0].band == Band.INTERMEDIATE
    assert segments[0].start.hour == 17


# Datas sem fuso (sem tzinfo) são recusadas com um ValueError que fala em "fuso".
def test_data_sem_fuso_e_recusada(tariff):
    with pytest.raises(ValueError, match="fuso"):
        split_by_band(datetime(2026, 9, 21, 17), datetime(2026, 9, 21, 18), tariff, NO_HOLIDAYS, TZ)


# Uma tarifa mal configurada: ponta 18h-21h e intermediário 20h-22h disputam as 20h-21h. validate()
# recusa com InvalidTariffError. "{b: ... for b in Band}" dá o mesmo preço a todas as faixas.
def test_janelas_sobrepostas_sao_recusadas():
    prices = {b: BandPrice(Decimal("0.3"), Decimal("1")) for b in Band}
    tariff = TariffSpec(
        name="inválida",
        prices=prices,
        windows=(TimeWindow(Band.PEAK, time(18), time(21)), TimeWindow(Band.INTERMEDIATE, time(20), time(22))),
    )
    with pytest.raises(InvalidTariffError, match="sobrepostas"):
        tariff.validate()


# Toda tarifa precisa do preço fora de ponta, que é a faixa padrão do dia. Esta só tem o preço da ponta.
def test_tarifa_sem_preco_fora_de_ponta_e_recusada():
    tariff = TariffSpec(name="sem padrão", prices={Band.PEAK: BandPrice(Decimal("0"), Decimal("1"))}, windows=())
    with pytest.raises(InvalidTariffError, match="fora de ponta"):
        tariff.validate()