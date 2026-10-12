import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { useQuery } from '../hooks/useQuery';
import { HomePage } from './HomePage';
import { invoiceClosingAt, selectCurrentInvoice } from '../utils/finance';

vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {}, user: { id: 2, name: 'Morador Teste', role: 'resident', unit_id: 1 } }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const query = (data: unknown) => ({ data, loading: false, error: '', retry: vi.fn() });
const october = { id: 1, period: '2026-10-01', total: '4.04', status: 'open' };
const november = { id: 2, period: '2026-11-01', total: '0.00', status: 'closed' };
const now = Date.parse('2026-10-12T12:00:00-03:00');
function show(rows: unknown[]) {
  vi.mocked(useQuery).mockReturnValueOnce(query([])).mockReturnValueOnce(query([])).mockReturnValueOnce(query([])).mockReturnValueOnce(query(rows));
  return renderToStaticMarkup(<HomePage onNavigate={vi.fn()} />);
}
beforeEach(() => { vi.mocked(useQuery).mockReset(); vi.spyOn(Date, 'now').mockReturnValue(now); });
afterEach(() => vi.restoreAllMocks());
describe('fatura do mês e precedência temporal', () => {
  it('destaca outubro e preserva o valor real quando novembro futuro é zero', () => {
    const html = show([november, october]);
    expect(html).toContain('Fatura do mês');
    expect(html).toContain('href="#faturas/1"');
    expect(html).toContain('4,04');
    expect(html).not.toContain('href="#faturas/2"');
  });
  it('fatura atual zero é legítima e não é substituída por uma antiga com consumo', () => {
    const html = show([{ ...october, total: '0.00' }, { ...october, id: 4, period: '2026-09-01' }]);
    expect(html).toContain('href="#faturas/1"');
    expect(html).toContain('0,00');
  });
  it('sem fatura atual, usa a mais recente anterior', () => {
    const rows = [{ ...october, id: 3, period: '2026-08-01' }, { ...october, id: 4, period: '2026-09-01' }, november];
    expect(show(rows)).toContain('href="#faturas/4"');
    expect(selectCurrentInvoice(rows, now)?.id).toBe(4);
    expect(rows.map(r => r.id)).toEqual([3, 4, 2]);
  });
  it.each([{ rows: [] }, { rows: [november] }])('sem elegíveis, explica e oferece a lista (%j)', ({ rows }) => {
    const html = show(rows);
    expect(html).toContain('Nenhuma fatura atual disponível');
    expect(html).toContain('Consultar todas as faturas');
    expect(html).not.toContain('Entender minha fatura');
  });
  it('a mudança de mês obedece São Paulo, incluindo transição de ano', () => {
    const boundary = Date.parse(invoiceClosingAt('2026-10-01'));
    expect(boundary).toBe(Date.parse('2026-11-01T03:00:00Z'));
    expect(selectCurrentInvoice([november, october], boundary - 1)?.id).toBe(1);
    expect(selectCurrentInvoice([november, october], boundary)?.id).toBe(2);
    expect(invoiceClosingAt('2026-12-01')).toBe('2027-01-01T00:00:00-03:00');
  });
});
