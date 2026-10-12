import { ApiError } from '../api/client';
const condoTimezone = 'America/Sao_Paulo';
export function formatDate(value: string) { return new Intl.DateTimeFormat('pt-BR', { timeZone: condoTimezone, day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)); }
export function formatTime(value: string) { return new Intl.DateTimeFormat('pt-BR', { timeZone: condoTimezone, hour: '2-digit', minute: '2-digit' }).format(new Date(value)); }
export function condoDate(value = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: condoTimezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(value);
  const part = (key: string) => parts.find(item => item.type === key)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}
// Horário do condomínio no período acadêmico: UTC−03:00, independente do navegador.
export function reservationTimestamp(date: string, time: string) { return `${date}T${time.length === 5 ? `${time}:00` : time}-03:00`; }
export type ReservationDraft = { charger_id: number; starts_at: string; ends_at: string };
export function condoInputTime(value: string) {
  return new Intl.DateTimeFormat('en-GB', { timeZone: condoTimezone, hourCycle: 'h23', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value));
}
export function draftTimestamp(date: string, time: string, original?: string) {
  return original && date === condoDate(new Date(original)) && time === condoInputTime(original)
    ? original : reservationTimestamp(date, time);
}
export function formatMoney(value: string) { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value)); }
export function formatEnergy(value: string) { return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(Number(value))} kWh`; }
export function formatPeriod(value: string) {
  const [year, month] = value.split('-').map(Number);
  return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(year, month - 1, 1)));
}
export function statusLabel(value: string, kind: 'end' | 'validation' | 'source') {
  const labels = {
    end: { completed: 'Concluída', user_stopped: 'Encerrada pelo usuário', system_failure: 'Falha do sistema', abnormal_disconnection: 'Desconexão anormal' },
    validation: { pending: 'Pendente', approved: 'Aprovada para cobrança', suspended: 'Suspensa para revisão', rejected: 'Rejeitada' },
    source: { simulator: 'Simulação', sems: 'SEMS', gateway: 'Gateway' },
  };
  return (labels[kind] as Record<string, string>)[value] ?? value;
}
export function record(value: unknown): Record<string, unknown> { return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
export function textList(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; }
export function errorMessage(error: unknown, validationMessage = 'Confira os campos informados e o intervalo da reserva (máximo de 12 horas).') {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Sua sessão terminou. Entre novamente para continuar.';
    if (typeof error.detail === 'string') return error.detail;
    if (error.status === 422) return validationMessage;
    if (error.status === 403) return 'Esta ação não está permitida para sua conta.';
    if (error.status === 404) return 'O registro não está disponível. Atualize a consulta.';
    if (error.status === 409) return 'O horário ou a situação da reserva mudou. Atualize a consulta e tente novamente.';
    return 'Não foi possível concluir a solicitação. Tente novamente.';
  }
  return 'Não foi possível conectar ao serviço. Confira a conexão e tente novamente.';
}
