import { condoDate, formatMoney } from './presentation';

export function invoiceClosingAt(period: string) {
  const [year, month] = period.split('-').map(Number);
  const day = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10);
  return `${day}T00:00:00-03:00`;
}
export function isFutureInvoice(period: string, now: number) {
  return period.slice(0, 7) > condoDate(new Date(now)).slice(0, 7);
}
export function selectCurrentInvoice<T extends { period: string }>(rows: T[], now: number): T | undefined {
  return [...rows].filter(row => !isFutureInvoice(row.period, now)).sort((a, b) => b.period.localeCompare(a.period))[0];
}

export function invoicePeriod(value: string) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return null;
  const [year, month] = value.split('-').map(Number);
  return year >= 2000 && year <= 2100 ? { year, month } : null;
}
// Formatação somente: a API é responsável por totais e parcelas.
export function reportMoney(value: unknown) {
  return typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) ? formatMoney(value) : 'Não informado';
}
export function reportCount(value: unknown) {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : 'Não informado';
}
export function formatUnitPrice(value: string) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(Number(value));
}
