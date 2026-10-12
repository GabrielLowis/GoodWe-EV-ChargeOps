import { describe, it, expect, vi } from 'vitest';
import { ApiError, createApiClient, unwrap } from './client';

describe('contrato HTTP', () => {
  it('usa o contrato gerado e envia o token somente no header', async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
      id: 2, name: 'Morador', email: 'morador@demo.local', role: 'resident', unit_id: 1,
      active: true, reservation_blocked_until: null,
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const api = createApiClient({ baseUrl: 'http://localhost:8000', token: () => 'test-token', fetch: fetcher });
    const user = unwrap(await api.GET('/api/usuarios/eu'));
    expect(user.role).toBe('resident');
    const request = fetcher.mock.calls[0][0] as Request;
    expect(request.url).toBe('http://localhost:8000/api/usuarios/eu');
    expect(request.headers.get('Authorization')).toBe('Bearer test-token');
    expect(request.url).not.toContain('test-token');
  });

  it('encerra a autenticação em 401 e preserva o detalhe da API', async () => {
    const logout = vi.fn();
    const api = createApiClient({ baseUrl: 'http://localhost:8000', onUnauthorized: logout,
      fetch: vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({ detail: 'Token expirado' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } })) });
    const result = await api.GET('/api/usuarios/eu');
    expect(() => unwrap(result)).toThrow('Token expirado');
    expect(logout).toHaveBeenCalledOnce();
  });

  it('preserva conflitos e validações sem confundir com sucesso', () => {
    expect(() => unwrap({ response: new Response(null, { status: 409 }), error: { detail: 'Janela ocupada' } }))
      .toThrow(ApiError);
    const detail = [{ loc: ['body', 'starts_at'], msg: 'Informe offset' }];
    try { unwrap({ response: new Response(null, { status: 422 }), error: { detail } }); }
    catch (error) { expect((error as ApiError).detail).toEqual(detail); }
  });
});
