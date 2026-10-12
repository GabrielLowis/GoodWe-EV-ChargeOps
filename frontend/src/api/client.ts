import createClient from 'openapi-fetch';
import type { paths } from './schema';

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly detail: unknown) {
    super(typeof detail === 'string' ? detail : `A API retornou o código ${status}.`);
    this.name = 'ApiError';
  }
}

export function createApiClient(options: {
  baseUrl?: string;
  token?: () => string | null;
  onUnauthorized?: () => void;
  fetch?: typeof fetch;
} = {}) {
  const client = createClient<paths>({ baseUrl: options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? '',
                                     fetch: options.fetch });
  client.use({
    onRequest({ request }) {
      const token = options.token?.();
      if (token) request.headers.set('Authorization', `Bearer ${token}`);
      return request;
    },
    onResponse({ response }) {
      if (response.status === 401) options.onUnauthorized?.();
      return response;
    },
  });
  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;

export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (!result.response.ok) {
    const error = result.error;
    const detail = error && typeof error === 'object' && 'detail' in error ? error.detail : error;
    throw new ApiError(result.response.status, detail);
  }
  if (result.data === undefined) throw new ApiError(result.response.status, 'Resposta vazia inesperada.');
  return result.data;
}
