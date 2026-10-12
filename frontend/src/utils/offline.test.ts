import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it, vi } from 'vitest';

const script = readFileSync(new URL('../../public/sw.js', import.meta.url), 'utf8');
function worker(online = false) {
  const events: Record<string, (event: unknown) => void> = {};
  const add = vi.fn(async () => {});
  const offline = new Response('<h1>Sem conexão</h1>');
  const onlineResponse = new Response('Aplicação online');
  const caches = { open: vi.fn(async () => ({ add })), match: vi.fn(async () => offline), keys: vi.fn(async () => []), delete: vi.fn(async () => true) };
  const fetch = vi.fn(async () => { if (!online) throw new Error('Serviço indisponível'); return onlineResponse; });
  const self = { location: { origin: 'http://localhost:4173' }, clients: { claim: vi.fn(async () => {}) }, addEventListener: (name: string, handler: (event: unknown) => void) => { events[name] = handler; } };
  runInNewContext(script, { self, caches, fetch, URL });
  return { events, caches, fetch, add, offline, onlineResponse };
}
describe('contingência PWA, em ambiente controlado', () => {
  it('instala somente a página de contingência', async () => {
    const test = worker();
    let installation: Promise<unknown> | undefined;
    test.events.install({ waitUntil: (promise: Promise<unknown>) => { installation = promise; } });
    await installation;
    expect(test.add.mock.calls).toEqual([['/offline.html']]);
  });
  it('mostra o aviso em uma navegação que falhou', async () => {
    const test = worker();
    let response: Promise<Response> | undefined;
    test.events.fetch({ request: { url: 'http://localhost:4173/', method: 'GET', mode: 'navigate' }, respondWith: (promise: Promise<Response>) => { response = promise; } });
    expect(await response).toBe(test.offline);
    expect(test.caches.match).toHaveBeenCalledWith('/offline.html');
  });
  it('mantém a resposta online quando a navegação funciona', async () => {
    const test = worker(true);
    let response: Promise<Response> | undefined;
    test.events.fetch({ request: { url: 'http://localhost:4173/', method: 'GET', mode: 'navigate' }, respondWith: (promise: Promise<Response>) => { response = promise; } });
    expect(await response).toBe(test.onlineResponse);
    expect(test.caches.match).not.toHaveBeenCalled();
  });
  it('não substitui consultas de API nem envio de ações por uma página em cache', () => {
    const test = worker();
    const respondWith = vi.fn();
    for (const request of [{ url: 'http://localhost:4173/api/faturas', method: 'GET', mode: 'cors' }, { url: 'http://localhost:4173/api/login', method: 'POST', mode: 'cors' }]) test.events.fetch({ request, respondWith });
    expect(respondWith).not.toHaveBeenCalled();
    expect(test.fetch).not.toHaveBeenCalled();
  });
});
