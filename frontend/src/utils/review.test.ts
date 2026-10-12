import { describe, expect, it } from 'vitest';
import { ApiError, createApiClient, unwrap } from '../api/client';
import type { components } from '../api/schema';
import { reviewBody } from './review';

const resident: components['schemas']['UserOut'] = { id: 2, name: 'Morador de teste', email: 'resident@example.test', role: 'resident', active: true, unit_id: 1, reservation_blocked_until: null };
const session: components['schemas']['SessionOut'] = { id: 7, source: 'simulator', external_id: 'fixture', charger_id: 1, connector: 1, card_id: null, reservation_id: null, user_id: null, attribution_method: 'unattributed', started_at: '2026-10-08T10:00:00-03:00', energy_ended_at: null, ended_at: '2026-10-08T11:00:00-03:00', total_kwh: '1.000', green_kwh: '0.000', grid_kwh: '1.000', average_power_kw: '1.00', max_power_kw: '1.00', end_status: 'completed', validation_status: 'suspended' };

describe('revisão de ocorrência', () => {
  it('exige um morador ativo para aprovação órfã e preserva a observação', () => {
    expect(() => reviewBody('approve', '', session, '', [resident])).toThrow('Selecione um morador ativo');
    expect(() => reviewBody('approve', '', session, '2', [{ ...resident, active: false }])).toThrow();
    expect(() => reviewBody('approve', '', session, '2', [{ ...resident, role: 'manager' }])).toThrow();
    expect(reviewBody('approve', '  Conferido com responsável.  ', session, '2', [resident])).toEqual({ decision: 'approve', note: 'Conferido com responsável.', user_id: 2 });
  });
  it('rejeita sem atribuir e mantém o responsável de sessões já identificadas', () => {
    expect(reviewBody('reject', '', session, '2', [resident])).toEqual({ decision: 'reject', note: null });
    expect(reviewBody('approve', 'Conferido.', { ...session, user_id: 2, reservation_id: 4 }, '3', [])).toEqual({ decision: 'approve', note: 'Conferido.' });
  });
  it('envia a decisão para a rota existente e preserva a recusa de revisão repetida', async () => {
    const requests: { path: string; body: unknown }[] = [];
    const api = createApiClient({ baseUrl: 'http://test.local', fetch: async (input: RequestInfo | URL) => {
      const request = input as Request;
      requests.push({ path: new URL(request.url).pathname, body: await request.json() });
      return new Response(JSON.stringify({ detail: 'Anomalia já revisada' }), { status: 409, headers: { 'Content-Type': 'application/json' } });
    } });
    const result = await api.POST('/api/anomalias/{anomaly_id}/revisao', { params: { path: { anomaly_id: 5 } }, body: reviewBody('approve', 'Conferido.', session, '2', [resident]) });
    expect(requests).toEqual([{ path: '/api/anomalias/5/revisao', body: { decision: 'approve', note: 'Conferido.', user_id: 2 } }]);
    expect(() => unwrap(result)).toThrow('Anomalia já revisada');
    try { unwrap(result); } catch (error) { expect(error).toBeInstanceOf(ApiError); expect((error as ApiError).status).toBe(409); }
  });
});
