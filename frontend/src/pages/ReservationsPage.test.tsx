import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import type { components } from '../api/schema';
import { useQuery } from '../hooks/useQuery';
import { ReservationList } from './ReservationsPage';
import { canCancelReservation, orderedReservations } from '../utils/reservations';

vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {} }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const start = Date.parse('2026-10-12T13:00:00-03:00');
const row: components['schemas']['ReservationOut'] = { id: 3, charger_id: 1, connector: 1, user_id: 2, status: 'active', starts_at: '2026-10-12T13:00:00-03:00', ends_at: '2026-10-12T14:00:00-03:00' };
function show(now: number, manager = false) {
  vi.spyOn(Date, 'now').mockReturnValue(now);
  vi.mocked(useQuery).mockReturnValue({ data: [row], loading: false, error: '', retry: vi.fn() });
  return renderToStaticMarkup(<ReservationList chargers={[]} residents={manager ? [] : undefined} />);
}
describe('cancelamento e história temporal, consultas controladas', () => {
  beforeEach(() => vi.mocked(useQuery).mockReset());
  afterEach(() => vi.restoreAllMocks());
  it.each([false, true])('oferece cancelamento antes do início (síndico=%s)', manager => {
    expect(show(start - 1, manager)).toContain('Cancelar reserva #3');
  });
  it.each([start, start + 1000, start + 3600_000])('não oferece a ação no início/depois: %s', now => {
    const html = show(now);
    expect(html).not.toContain('Cancelar reserva #3');
    expect(html).toContain(now >= start + 3600_000 ? 'Janela encerrada' : 'Janela iniciada');
    expect(html).toContain('Estado registrado: ativa');
  });
  it('reconsulta o instante no envio e não permite estados diferentes de active', () => {
    expect(canCancelReservation(row, start - 1)).toBe(true);
    expect(canCancelReservation(row, start)).toBe(false);
    for (const status of ['in_use', 'completed', 'cancelled', 'no_show'] as const) {
      expect(canCancelReservation({ ...row, status }, start - 1)).toBe(false);
    }
  });
  it('ordena futuras operáveis antes do histórico, sem alterar entrada', () => {
    const future = { ...row, id: 9, starts_at: '2026-10-13T10:00:00-03:00' };
    const later = { ...future, id: 10, starts_at: '2026-10-14T10:00:00-03:00' };
    const rows = [row, later, future];
    expect(orderedReservations(rows, start).map(r => r.id)).toEqual([9, 10, 3]);
    expect(rows.map(r => r.id)).toEqual([3, 10, 9]);
  });
});
