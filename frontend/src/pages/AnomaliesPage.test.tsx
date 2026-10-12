import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { useQuery } from '../hooks/useQuery';
import { ReviewForm } from './AnomaliesPage';
import type { components } from '../api/schema';

vi.mock('../auth/AuthProvider', () => ({ useAuth: () => ({ api: {} }) }));
vi.mock('../hooks/useQuery', () => ({ useQuery: vi.fn() }));
const anomaly: components['schemas']['AnomalyOut'] = { id: 8, session_id: 7, detected_at: '2026-10-08T10:00:00-03:00', detector: 'attribution', score: null, reasons: [{ code: 'ORPHAN_SESSION', message: 'Sem reserva correspondente.' }], status: 'pending_review', reviewed_by: null, reviewed_at: null, review_note: null };
const query = (data: unknown, loading = false) => ({ data, loading, error: '', retry: vi.fn() });
describe('formulário de revisão (dados controlados, sem banco)', () => {
  beforeEach(() => vi.mocked(useQuery).mockReset());
  it('exibe escolha obrigatória somente para uma sessão órfã e bloqueia aprovação sem seleção', () => {
    vi.mocked(useQuery).mockReturnValueOnce(query({ user_id: null })).mockReturnValueOnce(query([{ id: 2, name: 'Morador ativo', email: 'active@example.test', role: 'resident', active: true }, { id: 3, name: 'Morador inativo', role: 'resident', active: false }, { id: 1, name: 'Síndico', role: 'manager', active: true }]));
    const html = renderToStaticMarkup(<ReviewForm anomaly={anomaly} onReviewed={() => {}} />);
    expect(html).toContain('Morador responsável');
    expect(html).toContain('Morador ativo');
    expect(html).not.toContain('Morador inativo');
    expect(html).not.toContain('<option value="1">');
    expect(html).toMatch(/<select required=""/);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Confirmar revisão/);
    expect(html).toContain('maxLength="2000"');
  });
  it('mantém sessões identificadas sem campo para troca do morador', () => {
    vi.mocked(useQuery).mockReturnValueOnce(query({ user_id: 2 })).mockReturnValueOnce(query([{ id: 2, name: 'Responsável existente', role: 'resident', active: true }]));
    const html = renderToStaticMarkup(<ReviewForm anomaly={anomaly} onReviewed={() => {}} />);
    expect(html).toContain('Responsável existente');
    expect(html).not.toContain('Morador responsável');
    expect(html).toMatch(/<button class="button primary">Confirmar revisão/);
  });
  it('bloqueia decisão até os dados da sessão estarem disponíveis', () => {
    vi.mocked(useQuery).mockReturnValueOnce(query(undefined, true)).mockReturnValueOnce(query([]));
    const html = renderToStaticMarkup(<ReviewForm anomaly={anomaly} onReviewed={() => {}} />);
    expect(html).toContain('Consultando sessão');
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Confirmar revisão/);
  });
});
