import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { useQuery } from '../hooks/useQuery';
import { ManagerOverview } from './ManagerPage';

vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {}, user: { name: 'Síndico de teste' } }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const query = (data: unknown, error = '', loading = false) => ({ data, error, loading, retry: vi.fn() });
const reservation = (id: number, starts_at: string, status = 'active') => ({ id, starts_at, ends_at: starts_at, status, user_id: 2, charger_id: 1, connector: 1 });
const session = (id: number, started_at: string) => ({ id, started_at, total_kwh: '6.200', end_status: 'completed', validation_status: 'approved', source: 'simulator' });
function show(reservations: ReturnType<typeof query>, sessions: ReturnType<typeof query>) {
  vi.mocked(useQuery).mockReturnValueOnce(reservations).mockReturnValueOnce(sessions).mockReturnValueOnce(query([]));
  return renderToStaticMarkup(<ManagerOverview />);
}
describe('dashboard do síndico (consultas controladas, sem banco)', () => {
  beforeEach(() => { vi.mocked(useQuery).mockReset(); vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-10-11T12:00:00-03:00')); });
  afterEach(() => vi.restoreAllMocks());
  it('exclui reservas passadas, canceladas e já iniciadas, limita a três e mantém contagem total', () => {
    const rows = [reservation(1, '2026-10-09T13:00:00-03:00'), reservation(2, '2026-10-12T10:00:00-03:00', 'cancelled'), reservation(3, '2026-10-15T10:00:00-03:00'), reservation(4, '2026-10-12T10:00:00-03:00'), reservation(5, '2026-10-14T10:00:00-03:00'), reservation(6, '2026-10-13T10:00:00-03:00'), reservation(7, '2026-10-11T12:00:00-03:00'), reservation(8, '2026-10-12T11:00:00-03:00', 'in_use')];
    const html = show(query(rows), query([]));
    expect(html).toContain('<strong>8</strong>');
    expect(html.indexOf('Reserva #4')).toBeLessThan(html.indexOf('Reserva #6'));
    expect(html.indexOf('Reserva #6')).toBeLessThan(html.indexOf('Reserva #5'));
    for (const id of [1, 2, 3, 7, 8]) expect(html).not.toContain(`Reserva #${id}`);
    expect(rows.map(row => row.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });
  it('ordena três sessões por instante mais recente e oferece detalhes administrativos', () => {
    const rows = [session(1, '2026-10-08T10:00:00-03:00'), session(2, '2026-10-10T10:00:00-03:00'), session(3, '2026-10-09T10:00:00-03:00'), session(4, '2026-10-10T14:00:00Z')];
    const html = show(query([]), query(rows));
    expect(html.indexOf('Sessão #4')).toBeLessThan(html.indexOf('Sessão #2'));
    expect(html.indexOf('Sessão #2')).toBeLessThan(html.indexOf('Sessão #3'));
    expect(html).not.toContain('Sessão #1');
    expect(html).toContain('href="#sessoes/4"');
    expect(html).toContain('Simulação');
    expect(rows.map(row => row.id)).toEqual([1, 2, 3, 4]);
  });
  it('mantém sessões e contagem de anomalias quando a consulta de reservas falha', () => {
    const html = show(query(undefined, 'Reservas indisponíveis'), query([session(1, '2026-10-08T10:00:00-03:00')]));
    expect(html).toContain('Reservas indisponíveis');
    expect(html).toContain('Tentar novamente');
    expect(html).toContain('href="#sessoes/1"');
    expect(html).toContain('Anomalias pendentes');
  });
  it('mantém reservas enquanto sessões carregam e apresenta os dois estados vazios', () => {
    const loading = show(query([reservation(9, '2026-10-12T10:00:00-03:00')]), query(undefined, '', true));
    expect(loading).toContain('Reserva #9');
    expect(loading).toContain('Carregando sessões');
    const empty = show(query([]), query([]));
    expect(empty).toContain('Nenhuma reserva ativa futura agendada.');
    expect(empty).toContain('Nenhuma sessão registrada no condomínio.');
  });
});
