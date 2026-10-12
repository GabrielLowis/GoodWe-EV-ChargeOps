import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import type { components } from '../api/schema';
import { useQuery } from '../hooks/useQuery';
import { InvoiceDetail, InvoicesPage } from './InvoicesPage';

const auth = vi.hoisted(() => ({ role: 'manager' }));
vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {}, user: { role: auth.role } }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const amounts = { green_kwh: '1.000', grid_kwh: '5.200', idle_minutes: 0, green_amount: '0.30', grid_amount: '3.38', idle_amount: '0.00', subtotal: '3.68', tax_amount: '0.18', overhead_amount: '0.18', total: '4.04' };
const invoice: components['schemas']['InvoiceOut'] = { id: 1, user_id: 2, period: '2026-10-01', status: 'open', sessions_count: 1, ...amounts, calculation: { user: { name: 'Morador de teste' } }, engine_version: 'fixture', items: [{ id: 1, session_id: 7, tariff_id: 1, charge_rule: 'normal', is_late_entry: false, ...amounts, calculation: {} }] };
function show(data = invoice) {
  vi.mocked(useQuery).mockReturnValue({ data, loading: false, error: '', retry: vi.fn() });
  return renderToStaticMarkup(<InvoiceDetail id={1} administration backHref="#financeiro" backLabel="Voltar para o financeiro" />);
}
describe('detalhe compartilhado da fatura', () => {
  beforeEach(() => { auth.role = 'manager'; vi.mocked(useQuery).mockReset(); vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-10-12T12:00:00-03:00')); });
  afterEach(() => vi.restoreAllMocks());
  it('oferece fechamento após o período e usa o detalhe administrativo da sessão', () => {
    vi.mocked(Date.now).mockReturnValue(Date.parse('2026-11-01T00:00:00-03:00'));
    const html = show();
    expect(html).toContain('Fechar fatura #1');
    expect(html).toContain('href="#sessoes/7"');
    expect(html).toContain('href="#financeiro"');
    expect(html).toContain('4,04');
    expect(html).not.toContain('Confirmar fechamento');
  });
  it('durante o período explica e desabilita o fechamento', () => {
    const html = show();
    expect(html).toContain('Fechamento disponível a partir de');
    expect(html).toContain('01 de nov. de 2026');
    expect(html).toContain('disabled=""');
    expect(html).not.toContain('Confirmar fechamento');
  });
  it('mostra cálculo definitivo e não oferece fechamento da fatura já fechada', () => {
    const html = show({ ...invoice, status: 'closed' });
    expect(html).toContain('Esta fatura está fechada. Não pode ser recalculada.');
    expect(html).not.toContain('Fechar fatura #1');
  });
  it('preserva o acesso de leitura do morador mesmo com a opção administrativa', () => {
    auth.role = 'resident';
    const html = show();
    expect(html).not.toContain('Fechamento da fatura');
    expect(html).toContain('href="#recargas/7"');
  });
  it('identifica fatura futura na lista sem perder acesso ao detalhe', () => {
    vi.mocked(useQuery).mockReturnValue({ data: [{ ...invoice, id: 2, period: '2026-11-01', status: 'closed' }], loading: false, error: '', retry: vi.fn() });
    const html = renderToStaticMarkup(<InvoicesPage />);
    expect(html).toContain('Período futuro');
    expect(html).toContain('href="#faturas/2"');
  });
});
