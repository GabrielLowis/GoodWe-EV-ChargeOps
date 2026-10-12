import type { components } from '../api/schema';

type User = components['schemas']['UserOut'];
type Session = components['schemas']['SessionOut'];
export const reviewStatuses = ['pending_review', 'approved', 'rejected'] as const;
export const reviewLabels: Record<string, string> = { pending_review: 'Pendente', approved: 'Aprovada', rejected: 'Rejeitada' };

// Só a aprovação órfã envia atribuição; rejeitar não altera o responsável.
export function reviewBody(decision: 'approve' | 'reject', note: string, session: Session, residentId: string, users: User[]): components['schemas']['ReviewIn'] {
  const body: components['schemas']['ReviewIn'] = { decision, note: note.trim() || null };
  if (decision === 'approve' && session.user_id === null) {
    const resident = users.find(user => user.id === Number(residentId) && user.role === 'resident' && user.active);
    if (!resident) throw new Error('Selecione um morador ativo antes de aprovar esta sessão.');
    body.user_id = resident.id;
  }
  return body;
}
