import type { components } from '../api/schema';

type Reservation = components['schemas']['ReservationOut'];
export function canCancelReservation(row: Pick<Reservation, 'status' | 'starts_at'>, now: number) {
  return row.status === 'active' && Date.parse(row.starts_at) > now;
}
export function reservationTemporalLabel(row: Reservation, now: number) {
  if (row.status !== 'active' || Date.parse(row.starts_at) > now) return null;
  return Date.parse(row.ends_at) <= now ? 'Janela encerrada' : 'Janela iniciada';
}
export function orderedReservations(rows: Reservation[], now: number) {
  return [...rows].sort((a, b) => {
    const aFuture = canCancelReservation(a, now), bFuture = canCancelReservation(b, now);
    return Number(bFuture) - Number(aFuture) || (aFuture ? Date.parse(a.starts_at) - Date.parse(b.starts_at) : Date.parse(b.starts_at) - Date.parse(a.starts_at));
  });
}
