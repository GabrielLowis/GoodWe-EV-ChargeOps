import { describe, expect, it } from 'vitest';
import { formatUnitPrice, invoicePeriod, reportCount, reportMoney } from './finance';

describe('período e apresentação financeira', () => {
  it('envia ano/mês civil sem data ou fuso e recusa períodos inválidos', () => {
    expect(invoicePeriod('2026-11')).toEqual({ year: 2026, month: 11 });
    for (const invalid of ['', '2026-00', '2026-13', '2026-1', '1999-12', '2101-01', '2026-11-01']) expect(invoicePeriod(invalid)).toBeNull();
  });
  it('não transforma campos ausentes de relatório em zero', () => {
    expect(reportMoney('4.04')).toMatch(/4,04/);
    expect(reportMoney('0.00')).toMatch(/0,00/);
    for (const missing of [undefined, null, {}, 4.04, 'NaN']) expect(reportMoney(missing)).toBe('Não informado');
    expect(reportCount(0)).toBe('0');
    expect(reportCount(undefined)).toBe('Não informado');
  });
  it('preserva as quatro casas dos preços unitários na consulta', () => {
    expect(formatUnitPrice('0.2500')).toMatch(/0,2500/);
    expect(formatUnitPrice('1.4500')).toMatch(/1,4500/);
  });
});
