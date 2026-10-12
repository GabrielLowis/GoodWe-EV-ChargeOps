import { useCallback } from 'react';
import { unwrap } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { Icon, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { formatDate, formatEnergy, formatMoney, formatPeriod, formatTime } from '../utils/presentation';
import { SessionStatus } from './SessionsPage';
import { useTimeBoundaries } from '../hooks/useTimeBoundaries';
import { invoiceClosingAt, selectCurrentInvoice } from '../utils/finance';
import { condoDate } from '../utils/presentation';

export function HomePage({ onNavigate }: { onNavigate(page: 'nova-reserva' | 'reservas'): void }) {
  const { user, api } = useAuth();
  const units = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/unidades', { signal })), [api]));
  if (!user) return null;
  const manager = user.role === 'manager'; const unit = units.data?.find(item => item.id === user.unit_id);
  return <><div className="page-heading"><p className="eyebrow">{manager ? 'ÁREA ADMINISTRATIVA' : 'ÁREA DO MORADOR'}</p><h1>Olá, {user.name.split(' ')[0]}.</h1><p className="muted">{manager ? 'Bem-vindo à gestão de recarga do condomínio.' : 'Organize sua próxima recarga, no seu tempo.'}</p></div>
    <section className="welcome-card"><div><span className="section-kicker">{manager ? 'GESTÃO DO CONDOMÍNIO' : 'VAMOS AGENDAR?'}</span><h2>{manager ? 'Uma visão compartilhada da recarga.' : 'Um horário reservado para você.'}</h2><p>{manager ? 'Este é o início da sua área administrativa. Agenda do condomínio, sessões e revisões serão disponibilizadas nas próximas entregas.' : 'Escolha um carregador, consulte os horários ocupados e confirme sua reserva.'}</p>{!manager && <button className="button light" onClick={() => onNavigate('nova-reserva')}>Nova reserva<Icon name="arrow" /></button>}</div><span className="welcome-icon" aria-hidden="true"><Icon name="plug" /></span></section>
    {!manager && <ResidentOverview />}
    <div className="home-grid"><section className="card"><div className="card-heading"><h2>Minha conta</h2><span className="tag">{manager ? 'Síndico' : 'Morador'}</span></div><dl className="profile-details"><div><dt>Nome</dt><dd>{user.name}</dd></div><div><dt>E-mail</dt><dd>{user.email}</dd></div><div><dt>Unidade</dt><dd>{units.loading ? 'Carregando…' : units.error ? 'Consulta indisponível' : unit?.label ?? (user.unit_id === null ? 'Sem unidade vinculada' : 'Unidade não encontrada')}</dd></div></dl>{units.error && <QueryError message={units.error} retry={units.retry} />}</section>
    <section className="card"><h2>{manager ? 'Próximas entregas' : 'Acesso rápido'}</h2>{manager ? <p className="muted">A operação do síndico e o financeiro serão implementados nas entregas 3 e 4.</p> : <><button className="shortcut" onClick={() => onNavigate('reservas')}><span className="shortcut-icon"><Icon name="calendar" /></span><span><strong>Minhas reservas</strong><small>Consulte horários e cancele uma reserva ativa.</small></span><Icon name="arrow" /></button><a className="shortcut" href="#sugestao"><span className="shortcut-icon"><Icon name="clock-energy" /></span><span><strong>Sugestão de horário</strong><small>Consulte uma estimativa para planejar a recarga.</small></span><Icon name="arrow" /></a></>}</section></div>
    <p className="environment-note">Projeto acadêmico. A integração física com o carregador ainda não está conectada.</p></>;
}

function ResidentOverview() {
  const { api } = useAuth();
  const reservations = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/reservas', { signal })), [api]));
  const sessions = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/sessoes', { signal })), [api]));
  const invoices = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/faturas', { signal })), [api]));
  const next = reservations.data?.filter(item => item.status === 'active' && Date.parse(item.starts_at) > Date.now()).sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at))[0];
  const recent = [...(sessions.data ?? [])].sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at)).slice(0, 3);
  const now = useTimeBoundaries([Date.parse(invoiceClosingAt(condoDate().slice(0, 7)))]);
  const latest = selectCurrentInvoice(invoices.data ?? [], now);
  return <div className="overview-grid">
    <section className="card"><div className="card-heading"><h2>Próxima reserva</h2><Icon name="calendar" /></div>{reservations.loading ? <p role="status">Carregando reserva…</p> : reservations.error ? <QueryError message={reservations.error} retry={reservations.retry} /> : next ? <><p className="overview-value">{formatDate(next.starts_at)}<strong>{formatTime(next.starts_at)} – {formatDate(next.starts_at) !== formatDate(next.ends_at) && `${formatDate(next.ends_at)}, `}{formatTime(next.ends_at)}</strong></p><p className="muted small-text">Reserva #{next.id} · Conector {next.connector}</p><a href="#reservas">Ver minhas reservas →</a></> : <><p className="muted">Nenhuma reserva futura agendada.</p><a href="#nova-reserva">Agendar recarga →</a></>}</section>
    <section className="card"><div className="card-heading"><h2>{latest?.period.slice(0, 7) === condoDate(new Date(now)).slice(0, 7) ? 'Fatura do mês' : 'Fatura mais recente'}</h2><Icon name="receipt" /></div>{invoices.loading ? <p role="status">Carregando fatura…</p> : invoices.error ? <QueryError message={invoices.error} retry={invoices.retry} /> : latest ? <><p className="overview-value">{formatPeriod(latest.period)}<strong>{formatMoney(latest.total)}</strong></p><p><span className="tag">{latest.status === 'open' ? 'Aberta' : 'Fechada'}</span></p><a href={`#faturas/${latest.id}`}>Entender minha fatura →</a></> : <><p className="muted">Nenhuma fatura atual disponível.</p><a href="#faturas">Consultar todas as faturas →</a></>}</section>
    <section className="card overview-sessions"><div className="card-heading"><h2>Recargas recentes</h2><a href="#recargas">Ver todas →</a></div>{sessions.loading ? <p role="status">Carregando recargas…</p> : sessions.error ? <QueryError message={sessions.error} retry={sessions.retry} /> : !recent.length ? <p className="muted">Nenhuma recarga registrada.</p> : <ul className="data-list">{recent.map(session => <li key={session.id}><div><a className="item-title" href={`#recargas/${session.id}`}>Recarga #{session.id} · {formatDate(session.started_at)}</a><p>{formatEnergy(session.total_kwh)} · {formatTime(session.started_at)}</p><SessionStatus session={session} /></div><a href={`#recargas/${session.id}`} aria-label={`Ver recarga #${session.id}`}>Ver detalhes →</a></li>)}</ul>}</section>
  </div>;
}
