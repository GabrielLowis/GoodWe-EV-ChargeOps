import { useCallback } from 'react';
import { unwrap } from '../api/client';
import type { components } from '../api/schema';
import { useAuth } from '../auth/AuthProvider';
import { QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { formatDate, formatEnergy, formatPeriod, formatTime, statusLabel } from '../utils/presentation';

type Session = components['schemas']['SessionOut'];
export function SessionStatus({ session }: { session: Session }) {
  return <div className="session-badges"><span className="tag">{statusLabel(session.end_status, 'end')}</span><span className={`status status-${session.validation_status}`}>{statusLabel(session.validation_status, 'validation')}</span><span className="tag">{statusLabel(session.source, 'source')}</span></div>;
}
export function SessionsPage({ id }: { id?: number }) {
  return <><div className="page-heading"><p className="eyebrow">SEU HISTÓRICO DE RECARGA</p><h1>{id ? 'Detalhe da recarga' : 'Minhas recargas'}</h1><p className="muted">Confira a energia registrada e a situação de cada recarga.</p></div>{id ? <SessionDetail id={id} /> : <SessionList />}</>;
}
function SessionList() {
  const { api } = useAuth();
  const sessions = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes', { signal })), [api]));
  return <section className="card"><div className="card-heading"><h2>Histórico</h2><button className="button secondary small" disabled={sessions.loading} onClick={sessions.retry}>Atualizar lista</button></div>
    {sessions.loading ? <p role="status">Carregando recargas…</p> : sessions.error ? <QueryError message={sessions.error} retry={sessions.retry} /> : !sessions.data?.length ? <p className="muted">Nenhuma recarga registrada para sua conta.</p> : <ul className="data-list">{[...sessions.data].sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at)).map(session => <li key={session.id}><div><a className="item-title" href={`#recargas/${session.id}`}>Recarga #{session.id}</a><p>{formatDate(session.started_at)} · {formatTime(session.started_at)} · {formatEnergy(session.total_kwh)}</p><SessionStatus session={session} /></div><a className="button secondary small" href={`#recargas/${session.id}`}>Ver recarga #{session.id}</a></li>)}</ul>}
  </section>;
}
// Reutilizável na área do síndico; acesso aos dados continua autorizado pela API.
export function SessionDetail({ id, backHref = '#recargas', backLabel = 'Voltar para minhas recargas' }: { id: number; backHref?: string; backLabel?: string }) {
  const { api, user } = useAuth();
  const session = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes/{session_id}', { signal, params: { path: { session_id: id } } })), [api, id]));
  const chargers = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/carregadores', { signal })), [api]));
  const data = session.data;
  const timestamp = (value: string | null) => value ? `${formatDate(value)}, ${formatTime(value)}` : 'Não informado';
  return <><a className="back-link" href={backHref}>← {backLabel}</a><section className="card">
    {session.loading ? <p role="status">Carregando recarga…</p> : session.error ? <QueryError message={session.error} retry={session.retry} /> : data && <>
      <div className="card-heading"><h2>Recarga #{data.id}</h2><span className="tag">{statusLabel(data.source, 'source')}</span></div>
      {user?.role === 'manager' && <SessionOwner session={data} />}
      <div className="metric-grid"><div><span>Energia total</span><strong>{formatEnergy(data.total_kwh)}</strong></div><div><span>Green · solar/bateria</span><strong>{formatEnergy(data.green_kwh)}</strong></div><div><span>Grid · rede elétrica</span><strong>{formatEnergy(data.grid_kwh)}</strong></div></div>
      <dl className="detail-list"><div><dt>Reserva</dt><dd>{data.reservation_id === null ? 'Sem reserva vinculada' : <a href={user?.role === 'manager' ? '#agenda' : '#reservas'}>Reserva #{data.reservation_id}</a>}</dd></div><div><dt>Carregador / conector</dt><dd>{chargers.loading ? 'Carregando…' : `${chargers.data?.find(charger => charger.id === data.charger_id)?.code ?? `Carregador #${data.charger_id}`} · Conector ${data.connector}`}</dd></div><div><dt>Início</dt><dd>{timestamp(data.started_at)}</dd></div><div><dt>Fim da energia</dt><dd>{timestamp(data.energy_ended_at)}</dd></div><div><dt>Encerramento</dt><dd>{timestamp(data.ended_at)}</dd></div><div><dt>Situação da recarga</dt><dd>{statusLabel(data.end_status, 'end')}</dd></div><div><dt>Validação para cobrança</dt><dd>{statusLabel(data.validation_status, 'validation')}</dd></div><div><dt>Origem</dt><dd>{statusLabel(data.source, 'source')}</dd></div><div><dt>Potência média / máxima</dt><dd>{data.average_power_kw ? `${data.average_power_kw.replace('.', ',')} kW` : 'Não informado'} / {data.max_power_kw ? `${data.max_power_kw.replace('.', ',')} kW` : 'Não informado'}</dd></div></dl>
      {chargers.error && <QueryError message={chargers.error} retry={chargers.retry} />}
      <SessionBilling session={data} />
      <p className="environment-note">Uma recarga concluída pode aguardar validação. Aprovação para cobrança não indica pagamento.{data.source === 'simulator' && ' Esta recarga foi simulada; não comprova uso de equipamento físico.'}</p>
    </>}
  </section></>;
}

export function SessionBilling({ session }: { session: Session }) {
  const { api, user } = useAuth();
  const invoices = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/faturas', { signal })), [api]));
  const included = invoices.data?.find(invoice => invoice.items.some(item => item.session_id === session.id));
  let message = 'Ainda não incluída em fatura.';
  if (session.validation_status === 'rejected') message = 'Rejeitada para cobrança; não incluída em fatura.';
  else if (session.user_id === null) message = 'Sem morador responsável identificado; aguardando identificação e revisão.';
  else if (session.validation_status === 'pending' || session.validation_status === 'suspended') message = 'Aguardando validação/revisão para cobrança.';
  return <section className="detail-section"><h3>Vínculo de faturamento</h3>
    {invoices.loading ? <p role="status">Consultando vínculo de faturamento…</p> : invoices.error ? <QueryError message={invoices.error} retry={invoices.retry} /> : included ? <p>Incluída na fatura de <a href={`${user?.role === 'manager' ? '#financeiro' : '#faturas'}/${included.id}`}>{formatPeriod(included.period)} · Fatura #{included.id}</a>.</p> : <p>{message}</p>}
    <p className="muted small-text">Inclusão em fatura indica faturamento; o sistema não registra pagamentos.</p>
  </section>;
}

function SessionOwner({ session }: { session: Session }) {
  const { api } = useAuth();
  const users = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/usuarios', { signal })), [api]));
  return <><dl className="detail-list"><div><dt>Morador</dt><dd>{session.user_id === null ? 'Sem morador identificado' : users.loading ? 'Consultando…' : users.data?.find(user => user.id === session.user_id)?.name ?? `Morador #${session.user_id}`}</dd></div><div><dt>Atribuição</dt><dd>{({ reservation: 'Pela reserva', manual: 'Revisão manual', unattributed: 'Aguardando identificação' } as Record<string, string>)[session.attribution_method] ?? session.attribution_method}</dd></div></dl>{users.error && <QueryError message={users.error} retry={users.retry} />}</>;
}
