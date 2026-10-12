import { useCallback, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, unwrap } from '../api/client';
import type { components } from '../api/schema';
import { useAuth } from '../auth/AuthProvider';
import { Alert, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { errorMessage, formatDate, formatTime } from '../utils/presentation';
import { reviewBody, reviewLabels, reviewStatuses } from '../utils/review';
import { SessionDetail } from './SessionsPage';

type Anomaly = components['schemas']['AnomalyOut'];
export function AnomaliesPage({ id }: { id?: number }) {
  const { api } = useAuth();
  const [status, setStatus] = useState('pending_review');
  const [notice, setNotice] = useState('');
  const [failure, setFailure] = useState('');
  const anomalies = useQuery(useCallback(async (signal: AbortSignal) => {
    // A API oferece lista por situação, sem uma rota de detalhe de anomalia.
    const lists = await Promise.all((id ? reviewStatuses : [status]).map(value => api.GET('/api/anomalias', { signal, params: { query: { status: value } } }).then(unwrap)));
    const rows = lists.flat();
    if (id && !rows.some(row => row.id === id)) throw new ApiError(404, 'Ocorrência não encontrada.');
    return rows;
  }, [api, id, status]));
  const anomaly = anomalies.data?.find(row => row.id === id);
  function reviewed(message: string, error = false) { setNotice(error ? '' : message); setFailure(error ? message : ''); anomalies.retry(); }
  return <><div className="page-heading"><p className="eyebrow">VALIDAÇÃO DAS RECARGAS</p><h1>{id ? `Ocorrência #${id}` : 'Fila de anomalias'}</h1><p className="muted">Confira os motivos e os dados registrados antes de decidir sobre a cobrança.</p></div>
    {id && <a className="back-link" href="#anomalias">← Voltar para a fila de anomalias</a>}{notice && <Alert success>{notice}</Alert>}{failure && <Alert>{failure}</Alert>}
    <section className="card"><div className="card-heading"><h2>{id ? 'Motivos e revisão' : 'Ocorrências'}</h2><button className="button secondary small" disabled={anomalies.loading} onClick={anomalies.retry}>Atualizar {id ? 'ocorrência' : 'lista'}</button></div>
      {!id && <label className="filter-field">Situação<select value={status} onChange={event => setStatus(event.target.value)}>{reviewStatuses.map(value => <option key={value} value={value}>{reviewLabels[value]}</option>)}</select></label>}
      {anomalies.loading ? <p role="status">Carregando ocorrências…</p> : anomalies.error ? <QueryError message={anomalies.error} retry={anomalies.retry} /> : id && anomaly ? <>
        <div className="session-badges"><span className={`status status-${anomaly.status}`}>{reviewLabels[anomaly.status] ?? anomaly.status}</span><span className="tag">Sessão #{anomaly.session_id}</span></div>
        <p className="small-text muted">Detectada em {formatDate(anomaly.detected_at)}, {formatTime(anomaly.detected_at)}.</p>
        {anomaly.reasons.length ? <ul className="explanation-list">{anomaly.reasons.map((reason, index) => <li key={index}>{typeof reason.message === 'string' ? reason.message : typeof reason.code === 'string' ? `Motivo informado: ${reason.code}` : 'Descrição não informada.'}{typeof reason.model_version === 'string' && <small> · Modelo {reason.model_version}</small>}</li>)}</ul> : <p className="muted">Motivos não informados pela API.</p>}
        <dl className="detail-list"><div><dt>Detecção</dt><dd>{({ rules: 'Regras de validação', ml: 'Modelo estatístico', scope: 'Escopo do modelo', attribution: 'Identificação do morador', passed: 'Verificações automáticas' } as Record<string, string>)[anomaly.detector] ?? anomaly.detector}</dd></div><div><dt>Score retornado</dt><dd>{anomaly.score ?? 'Não informado'}</dd></div></dl><p className="environment-note">O score do detector não representa uma probabilidade calibrada. A ocorrência exige conferência dos dados.</p>
        {anomaly.status === 'pending_review' ? <ReviewForm anomaly={anomaly} onReviewed={reviewed} /> : <div className="detail-section"><h3>Revisão registrada</h3><dl className="detail-list"><div><dt>Data</dt><dd>{anomaly.reviewed_at ? `${formatDate(anomaly.reviewed_at)}, ${formatTime(anomaly.reviewed_at)}` : 'Não informado'}</dd></div><div><dt>Responsável</dt><dd>{anomaly.reviewed_by ? `Síndico #${anomaly.reviewed_by}` : 'Não informado'}</dd></div><div><dt>Observação</dt><dd>{anomaly.review_note ?? 'Não informada'}</dd></div></dl></div>}
      </> : !anomalies.data?.length ? <p className="muted">Nenhuma ocorrência {status === 'pending_review' ? 'pendente' : status === 'approved' ? 'aprovada' : 'rejeitada'} registrada.</p> : <ul className="data-list">{anomalies.data.map(row => <li key={row.id}><div><a className="item-title" href={`#anomalias/${row.id}`}>Ocorrência #{row.id} · Sessão #{row.session_id}</a><p>{formatDate(row.detected_at)}, {formatTime(row.detected_at)}</p><span className={`status status-${row.status}`}>{reviewLabels[row.status] ?? row.status}</span></div><a className="button secondary small" href={`#anomalias/${row.id}`}>Conferir ocorrência #{row.id}</a></li>)}</ul>}
    </section>{anomaly && <div className="detail-section"><SessionDetail key={`${anomaly.id}-${anomaly.status}`} id={anomaly.session_id} backHref={`#sessoes/${anomaly.session_id}`} backLabel="Abrir detalhe da sessão" /></div>}
  </>;
}

export function ReviewForm({ anomaly, onReviewed }: { anomaly: Anomaly; onReviewed(message: string, error?: boolean): void }) {
  const { api } = useAuth();
  const session = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes/{session_id}', { signal, params: { path: { session_id: anomaly.session_id } } })), [api, anomaly.session_id]));
  const users = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/usuarios', { signal })), [api]));
  const [decision, setDecision] = useState<'approve' | 'reject'>('approve');
  const [residentId, setResidentId] = useState('');
  const [note, setNote] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const residents = users.data?.filter(user => user.role === 'resident' && user.active) ?? [];
  const orphan = session.data?.user_id === null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || !session.data) return;
    setError('');
    let body: components['schemas']['ReviewIn'];
    try { body = reviewBody(decision, note, session.data, residentId, residents); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Confira o morador selecionado.'); return; }
    try {
      setPending(true);
      unwrap(await api.POST('/api/anomalias/{anomaly_id}/revisao', { params: { path: { anomaly_id: anomaly.id } }, body }));
      onReviewed(`Ocorrência #${anomaly.id} ${decision === 'approve' ? 'aprovada' : 'rejeitada'}. A revisão foi registrada.`);
    } catch (reason) {
      const message = errorMessage(reason, 'Confira a decisão e o morador selecionado.');
      if (reason instanceof ApiError && reason.status === 409) onReviewed(message, true);
      else setError(message);
    } finally { setPending(false); }
  }
  return <form className="detail-section review-form" onSubmit={submit}><h3>Registrar decisão</h3>{session.loading && <p role="status">Consultando sessão…</p>}{session.error && <QueryError message={session.error} retry={session.retry} />}{error && <Alert>{error}</Alert>}
    <label>Decisão<select value={decision} disabled={pending} onChange={event => { setDecision(event.target.value as 'approve' | 'reject'); setError(''); }}><option value="approve">Aprovar para cobrança</option><option value="reject">Rejeitar para cobrança</option></select></label>
    {orphan ? <><p className="draft-note">Esta sessão não tem morador identificado. Para aprovar, selecione o responsável ativo. A rejeição não atribui um morador.</p>{decision === 'approve' && <>{users.loading ? <p role="status">Consultando moradores…</p> : users.error ? <QueryError message={users.error} retry={users.retry} /> : <label>Morador responsável<select required value={residentId} disabled={pending} onChange={event => setResidentId(event.target.value)}><option value="">Selecione o morador</option>{residents.map(resident => <option key={resident.id} value={resident.id}>{resident.name} · {resident.email}</option>)}</select></label>}{!users.loading && !users.error && !residents.length && <p role="alert">Não há moradores ativos disponíveis para atribuição.</p>}</>}</> : session.data && <p className="small-text muted">Responsável: {users.data?.find(user => user.id === session.data?.user_id)?.name ?? `Morador #${session.data.user_id}`}. A revisão mantém a atribuição existente.</p>}
    <label>Observação<textarea rows={4} maxLength={2000} value={note} disabled={pending} onChange={event => setNote(event.target.value)} placeholder="Registre o que foi conferido e o motivo da decisão." /></label><p className="small-text muted">Até 2.000 caracteres. A decisão atualiza a validação da sessão.</p><button className={`button ${decision === 'approve' ? 'primary' : 'danger'}`} disabled={pending || session.loading || !session.data || (decision === 'approve' && orphan && (users.loading || !!users.error || !residentId))}>{pending ? 'Registrando…' : 'Confirmar revisão'}</button>
  </form>;
}
