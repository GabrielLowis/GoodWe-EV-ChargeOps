import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import type { components } from '../api/schema';
import { useQuery } from '../hooks/useQuery';
import { SessionBilling } from './SessionsPage';

const auth = vi.hoisted(() => ({ role: 'resident' }));
vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {}, user: { role: auth.role } }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const session: components['schemas']['SessionOut'] = { id: 1, external_id: '42', source: 'simulator', charger_id: 1, connector: 1, card_id: null, reservation_id: 1, user_id: 2, attribution_method: 'reservation', started_at: '2026-10-08T01:00:00-03:00', ended_at: '2026-10-08T04:00:00-03:00', energy_ended_at: null, total_kwh: '6.200', green_kwh: '1.000', grid_kwh: '5.200', average_power_kw: '2.30', max_power_kw: '3.30', end_status: 'completed', validation_status: 'approved' };
const invoice = { id: 3, period: '2026-11-01', items: [{ session_id: 1, is_late_entry: true }] };
function show(data: unknown, current = session, error = '', loading = false) {
  vi.mocked(useQuery).mockReturnValue({ data, error, loading, retry: vi.fn() });
  return renderToStaticMarkup(<SessionBilling session={current} />);
}
beforeEach(() => { auth.role = 'resident'; vi.mocked(useQuery).mockReset(); });
describe('destino comprovado da cobrança da recarga', () => {
  it.each([{ role: 'resident', path: '#faturas/3' }, { role: 'manager', path: '#financeiro/3' }])('link por perfil e período real do lançamento posterior ($role)', ({ role, path }) => {
    auth.role = role;
    const html = show([invoice]);
    expect(html).toContain(`href="${path}"`);
    expect(html).toContain('novembro de 2026');
    expect(html).toContain('Incluída na fatura');
  });
  it('não usa external_id como id da sessão nem afirma inclusão inexistente', () => {
    const html = show([{ ...invoice, items: [{ session_id: 42 }] }]);
    expect(html).toContain('Ainda não incluída em fatura');
    expect(html).not.toContain('href="#faturas/3"');
  });
  it('erro de consulta permite repetição sem afirmar ausência de faturamento', () => {
    const html = show(undefined, session, 'Consulta financeira indisponível');
    expect(html).toContain('Consulta financeira indisponível');
    expect(html).toContain('Tentar novamente');
    expect(html).not.toContain('Ainda não incluída');
    expect(html).not.toContain('Incluída na fatura');
  });
  it('carregamento não apresenta conclusão financeira', () => {
    const html = show(undefined, session, '', true);
    expect(html).toContain('Consultando vínculo de faturamento');
    expect(html).not.toContain('Ainda não incluída');
  });
  it.each(['pending', 'suspended'])('descreve revisão comprovada (%s)', validation_status => {
    expect(show([], { ...session, validation_status })).toContain('Aguardando validação/revisão');
  });
  it('distingue sessão órfã e rejeitada', () => {
    expect(show([], { ...session, user_id: null })).toContain('Sem morador responsável identificado');
    expect(show([], { ...session, user_id: null, validation_status: 'rejected' })).toContain('Rejeitada para cobrança');
  });
});
