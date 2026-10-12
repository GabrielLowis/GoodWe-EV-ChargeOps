## Classificação de horários em faixas e divisão da sessão em trechos. ##

"""Regra da Sprint 2: se a recarga começa em uma faixa e termina em outra, a
cobrança é particionada por intervalo. Nunca se usa a tarifa do horário
inicial para a sessão inteira.

Exemplo do plano: 17:30-18:00 intermediário + 18:00-20:30 ponta. """

# # Ideia geral: pense numa régua de horários com marcas onde a faixa pode mudar. O motor anda de marca em marca, do início ao fim da carga, e anota 

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from backend.db.enums import Band
from backend.rateio.models import HolidaySet, Segment, TariffSpec

# O dia inteiro é fora de ponta? weekday() numera os dias de 0 (segunda) a 6 (domingo), então ">= 5" quer dizer sábado ou domingo. "day in holidays" confere se a data está na lista de feriados.
def is_off_peak_day(day: date, tariff: TariffSpec, holidays: HolidaySet) -> bool:
    # Sábados, domingos e feriados são fora de ponta o dia todo (Tarifa Branca), se a tarifa assim definir.
    return tariff.weekends_holidays_off_peak and (day.weekday() >= 5 or day in holidays)

# Texto do tipo de dia, usado na memória de cálculo ("feriado", "fim de semana" ou "dia útil").
def day_type_label(day: date, holidays: HolidaySet) -> str:
    if day in holidays:
        return "feriado"
    if day.weekday() >= 5:
        return "fim de semana"
    return "dia útil"

# Em qual faixa cai um momento. Primeiro olha o tipo de dia; depois procura uma janela que contenha o horário (o início da janela conta e o fim não: 18:00 já é ponta, 21:00 já não é). 
def band_at(moment_local: datetime, tariff: TariffSpec, holidays: HolidaySet) -> Band:
    # Faixa vigente em um instante (já convertido para o horário local do condomínio).
    if is_off_peak_day(moment_local.date(), tariff, holidays):
        return Band.OFF_PEAK
    # Só a hora do dia, sem a data.
    clock = moment_local.time()
    for window in tariff.windows:
        if window.start <= clock < window.end:
            return window.band
    # Fora de todas as janelas: fora de ponta
    return Band.OFF_PEAK

# A próxima "marca da régua" depois de cursor: o início ou o fim de uma janela ainda naquele dia, ou a meia-noite seguinte (quando o tipo de dia pode mudar). min() escolhe a mais próxima.
def _next_boundary(cursor: datetime, tariff: TariffSpec, tz: ZoneInfo) -> datetime:
    """Próximo instante, depois de `cursor`, em que a faixa pode mudar.

    Candidatos: início e fim de cada janela no mesmo dia e a meia-noite
    seguinte (quando o tipo de dia pode mudar: útil -> sábado, véspera -> feriado).
    """
    day = cursor.date()
    # Datetime.combine junta uma data e um horário; aqui, o dia seguinte às 00:00.
    candidates = [datetime.combine(day + timedelta(days=1), time(0), tzinfo=tz)]
    for window in tariff.windows:
        for clock in (window.start, window.end):
            boundary = datetime.combine(day, clock, tzinfo=tz)
            if boundary > cursor:
                # Só interessam as marcas que ainda estão à frente
                candidates.append(boundary)
    return min(candidates)

# Divide a carga em trechos, cada um inteiro dentro de uma faixa.
def split_by_band(
    start: datetime,
    end: datetime,
    tariff: TariffSpec,
    holidays: HolidaySet,
    tz: ZoneInfo,
) -> list[Segment]:
    """Divide o intervalo [start, end) em trechos de faixa constante.

    Trechos vizinhos com a mesma faixa são unidos (ex.: 22:00 de sexta até
    02:00 de sábado vira um único trecho fora de ponta).
    """
    # Sem fuso não dá para saber que horas eram no condomínio, então o motor recusa.
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Datas sem fuso horário: informe o offset (ex.: -03:00)")
    tariff.validate()

    # Converte para o horário do condomínio antes de classificar.
    cursor = start.astimezone(tz)
    finish = end.astimezone(tz)
    if finish <= cursor:
        # Sessão sem duração: um trecho vazio na faixa do início
        return [Segment(cursor, cursor, band_at(cursor, tariff, holidays))]

    segments: list[Segment] = []
    # Anda de marca em marca até chegar ao fim da carga.
    while cursor < finish:
        segment_end = min(_next_boundary(cursor, tariff, tz), finish)
        band = band_at(cursor, tariff, holidays)
        # segments[-1] é o último trecho da lista. Se ele tem a mesma faixa, só estica o fim dele.
        if segments and segments[-1].band == band:
            segments[-1] = Segment(segments[-1].start, segment_end, band)
        else:
            segments.append(Segment(cursor, segment_end, band))
        cursor = segment_end
    # Avança para a próxima marca.
    return segments
