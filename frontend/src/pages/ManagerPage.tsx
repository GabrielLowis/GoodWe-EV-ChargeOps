import { useCallback } from 'react';
import { unwrap } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { formatDate, formatEnergy, formatTime } from '../utils/presentation';
import { ReservationList } from './ReservationsPage';
import { SessionDetail, SessionStatus } from './SessionsPage';

export function ManagerOverview() {
  const { api, user } = useAuth();
  const reservations = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/reservas', { signal })), [api]));
  const sessions = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes', { signal })), [api]));
  const anomalies = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/anomalias', { signal, params: { query: { status: 'pending_review' } } })), [api]));
  const upcoming = [...(reservations.data ?? [])]
    .filter(item => item.status === 'active' && Date.parse(item.starts_at) > Date.now())
    .sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at) || a.id - b.id).slice(0, 3);
  const recent = [...(sessions.data ?? [])]
    .sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at) || b.id - a.id).slice(0, 3);
  return <><div className="page-heading"><p className="eyebrow">OPERAÇÃO DO CONDOMÍNIO</p><h1>Visão geral</h1><p className="muted">Olá, {user?.name}. Acompanhe os registros e as revisões que precisam de atenção.</p></div><div className="manager-overview">{[
    { title: 'Reservas registradas', query: reservations, href: '#agenda', link: 'Abrir agenda' },
    { title: 'Sessões registradas', query: sessions, href: '#sessoes', link: 'Consultar sessões' },
    { title: 'Anomalias pendentes', query: anomalies, href: '#anomalias', link: 'Abrir fila de revisão' },
  ].map(({ title, query, href, link }) => <section className="card" key={href}><h2>{title}</h2>{query.loading ? <p role="status">Consultando…</p> : query.error ? <QueryError message={query.error} retry={query.retry} /> : <p className="overview-value"><strong>{query.data?.length ?? 0}</strong>{href === '#agenda' ? 'Inclui todos os estados da agenda.' : href === '#anomalias' ? 'Ocorrências aguardando decisão.' : 'Inclui simulações identificadas na lista.'}</p>}<a className="item-title" href={href}>{link} →</a><button className="text-button" aria-label={`Atualizar ${title.toLowerCase()}`} disabled={query.loading} onClick={query.retry}>Atualizar</button></section>)}</div>
    <div className="overview-grid manager-recent">
      <section className="card" aria-labelledby="upcoming-title">
        <div className="card-heading"><h2 id="upcoming-title">Próximas reservas</h2><button className="button secondary small" disabled={reservations.loading} onClick={reservations.retry}>Atualizar reservas</button></div>
        {reservations.loading ? <p role="status">Carregando reservas…</p> : reservations.error ? <QueryError message={reservations.error} retry={reservations.retry} /> : !upcoming.length ? <p className="muted">Nenhuma reserva ativa futura agendada.</p> : <ul className="data-list">{upcoming.map(item => <li key={item.id}><div><a className="item-title" href="#agenda">Reserva #{item.id}</a><p>{formatDate(item.starts_at)}, {formatTime(item.starts_at)} – {formatDate(item.starts_at) !== formatDate(item.ends_at) && `${formatDate(item.ends_at)}, `}{formatTime(item.ends_at)}</p><p>Morador #{item.user_id} · Carregador #{item.charger_id} · Conector {item.connector}</p></div></li>)}</ul>}
        <a href="#agenda">Ver agenda do condomínio →</a>
      </section>
      <section className="card" aria-labelledby="recent-title">
        <div className="card-heading"><h2 id="recent-title">Sessões recentes</h2><button className="button secondary small" disabled={sessions.loading} onClick={sessions.retry}>Atualizar sessões</button></div>
        {sessions.loading ? <p role="status">Carregando sessões…</p> : sessions.error ? <QueryError message={sessions.error} retry={sessions.retry} /> : !recent.length ? <p className="muted">Nenhuma sessão registrada no condomínio.</p> : <ul className="data-list">{recent.map(session => <li key={session.id}><div><a className="item-title" href={`#sessoes/${session.id}`}>Sessão #{session.id}</a><p>{formatDate(session.started_at)}, {formatTime(session.started_at)} · {formatEnergy(session.total_kwh)}</p><SessionStatus session={session} /><a className="back-link" href={`#sessoes/${session.id}`}>Ver sessão #{session.id} →</a></div></li>)}</ul>}
        <a href="#sessoes">Ver todas as sessões →</a>
      </section>
    </div><p className="environment-note">As contagens vêm dos registros da API. Não indicam disponibilidade física nem equipamento online.</p></>;
}

export function ManagerAgenda() {
  const { api } = useAuth();
  const chargers = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/carregadores', { signal })), [api]));
  const users = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/usuarios', { signal })), [api]));
  return <><div className="page-heading"><p className="eyebrow">HORÁRIOS COMPARTILHADOS</p><h1>Agenda do condomínio</h1><p className="muted">Consulte os moradores, os horários e a situação das reservas.</p></div>{chargers.error && <QueryError message={chargers.error} retry={chargers.retry} />}{users.error && <QueryError message={users.error} retry={users.retry} />}<ReservationList chargers={chargers.data ?? []} residents={users.data ?? []} /></>;
}

export function ManagerSessions({ id }: { id?: number }) {
  const { api } = useAuth();
  const sessions = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes', { signal })), [api]));
  const users = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/usuarios', { signal })), [api]));
  return <><div className="page-heading"><p className="eyebrow">USO REGISTRADO</p><h1>{id ? 'Detalhe da sessão' : 'Sessões do condomínio'}</h1><p className="muted">Encerramento e validação para cobrança são situações distintas.</p></div>{id ? <SessionDetail id={id} backHref="#sessoes" backLabel="Voltar para sessões do condomínio" /> : <section className="card"><div className="card-heading"><h2>Todas as sessões</h2><button className="button secondary small" disabled={sessions.loading || users.loading} onClick={() => { sessions.retry(); users.retry(); }}>Atualizar lista</button></div>{users.error && <QueryError message={users.error} retry={users.retry} />}{sessions.loading ? <p role="status">Carregando sessões…</p> : sessions.error ? <QueryError message={sessions.error} retry={sessions.retry} /> : !sessions.data?.length ? <p className="muted">Nenhuma sessão registrada no condomínio.</p> : <ul className="data-list">{sessions.data.map(session => <li key={session.id}><div><a className="item-title" href={`#sessoes/${session.id}`}>Sessão #{session.id}</a><p>{session.user_id === null ? 'Sem morador identificado' : users.data?.find(user => user.id === session.user_id)?.name ?? `Morador #${session.user_id}`} · {formatDate(session.started_at)}, {formatTime(session.started_at)} · {formatEnergy(session.total_kwh)}</p><SessionStatus session={session} /></div><a className="button secondary small" href={`#sessoes/${session.id}`}>Ver sessão #{session.id}</a></li>)}</ul>}</section>}</>;
}
