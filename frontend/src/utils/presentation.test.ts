import { describe, expect, it } from 'vitest';
import { condoDate, condoInputTime, draftTimestamp, formatPeriod, reservationTimestamp } from './presentation';

describe('datas da área do morador', () => {
  it('apresenta UTC no fuso de São Paulo, inclusive mudança de dia', () => {
    const value = '2026-10-09T01:30:17Z';
    expect(condoDate(new Date(value))).toBe('2026-10-08');
    expect(condoInputTime(value)).toBe('22:30:17');
  });
  it('preserva exatamente o intervalo sugerido, incluindo frações de segundo', () => {
    const start = '2026-10-09T15:00:00Z', end = '2026-10-09T16:51:25.714286Z';
    const actualStart = draftTimestamp('2026-10-09', '12:00:00', start);
    const actualEnd = draftTimestamp('2026-10-09', '13:51:25', end);
    expect(actualStart).toBe(start);
    expect(actualEnd).toBe(end);
    expect(Date.parse(actualEnd) - Date.parse(actualStart)).toBe(Date.parse(end) - Date.parse(start));
    expect(draftTimestamp('2026-10-09', '14:00:01', end)).toBe('2026-10-09T14:00:01-03:00');
    expect(reservationTimestamp('2026-10-09', '14:00')).toBe('2026-10-09T14:00:00-03:00');
  });
  it('mantém o mês civil da fatura sem deslocamento de fuso', () => {
    expect(formatPeriod('2026-10-01')).toBe('outubro de 2026');
    expect(formatPeriod('2026-01-01')).toBe('janeiro de 2026');
  });
});
