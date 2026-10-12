import { useCallback, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, unwrap } from '../api/client';
import type { components } from '../api/schema';
import { useAuth } from '../auth/AuthProvider';
import { Alert, Icon, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { condoDate, condoInputTime, draftTimestamp, errorMessage, formatDate, formatTime, reservationTimestamp } from '../utils/presentation';
import type { ReservationDraft } from '../utils/presentation';

type Charger = components['schemas']['ChargerOut'];
type Reservation = components['schemas']['ReservationOut'];
import { useTimeBoundaries } from '../hooks/useTimeBoundaries';
import { canCancelReservation, orderedReservations, reservationTemporalLabel } from '../utils/reservations';

const statusLabels: Record<Reservation['status'], string> = { active: 'Agendada', in_use: 'Em uso', completed: 'Concluída', cancelled: 'Cancelada', no_show: 'Não compareceu' };

export function ReservationsPage({ mode, notice, draft, onCreated }: { mode: 'create' | 'list'; notice: string; draft?: ReservationDraft; onCreated(): void }) {
  const { api } = useAuth();
  const chargers = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/carregadores', { signal })), [api]));
  return <>
    <div className="page-heading"><p className="eyebrow">SUA RECARGA, ORGANIZADA</p><h1>{mode === 'create' ? 'Nova reserva' : 'Minhas reservas'}</h1><p className="muted">{mode === 'create' ? 'Escolha o ponto de recarga e o melhor horário para sua rotina.' : 'Acompanhe seus agendamentos e libere os horários que não vai usar.'}</p></div>
    {notice && <Alert success>{notice}</Alert>}
    {chargers.error && <QueryError message={chargers.error} retry={chargers.retry} />}
    {mode === 'create' ? chargers.loading ? <div className="card" role="status">Carregando carregadores…</div> : chargers.data && <ReservationForm key={draft ? `${draft.charger_id}-${draft.starts_at}-${draft.ends_at}` : 'manual'} chargers={chargers.data.filter(charger => charger.active)} draft={draft} onCreated={onCreated} /> : <ReservationList chargers={chargers.data ?? []} />}
  </>;
}

function ReservationForm({ chargers, draft, onCreated }: { chargers: Charger[]; draft?: ReservationDraft; onCreated(): void }) {
  const { api, user } = useAuth();
  const [chargerId, setChargerId] = useState(String(draft?.charger_id ?? chargers[0]?.id ?? ''));
  const [connector, setConnector] = useState('1');
  const [date, setDate] = useState(draft ? condoDate(new Date(draft.starts_at)) : condoDate());
  const [endDate, setEndDate] = useState(draft ? condoDate(new Date(draft.ends_at)) : condoDate());
  const [startTime, setStartTime] = useState(draft ? condoInputTime(draft.starts_at) : '');
  const [endTime, setEndTime] = useState(draft ? condoInputTime(draft.ends_at) : '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [fields, setFields] = useState<Record<string, string>>({});
  const charger = chargers.find(item => item.id === Number(chargerId));
  const availability = useQuery(useCallback(async (signal: AbortSignal) => {
    if (!chargerId || !date) return null;
    const next = new Date(`${date}T12:00:00-03:00`); next.setUTCDate(next.getUTCDate() + 1);
    return unwrap(await api.GET('/api/carregadores/{charger_id}/disponibilidade', {
      signal, params: { path: { charger_id: Number(chargerId) }, query: { start: reservationTimestamp(date, '00:00'), end: reservationTimestamp(condoDate(next), '00:00') } },
    }));
  }, [api, chargerId, date]));
  const busy = availability.data?.busy.filter(item => item.connector === Number(connector)) ?? [];
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (pending) return;
    setError(''); setFields({});
    const startsAt = draftTimestamp(date, startTime, draft?.starts_at), endsAt = draftTimestamp(endDate, endTime, draft?.ends_at);
    const start = Date.parse(startsAt), end = Date.parse(endsAt);
    const invalid: Record<string, string> = {};
    if (!charger) invalid.charger_id = 'Escolha um carregador cadastrado.';
    if (!Number.isFinite(start) || start <= Date.now()) invalid.starts_at = 'Escolha uma data e um horário no futuro.';
    if (!Number.isFinite(end) || end <= start) invalid.ends_at = 'O fim precisa ocorrer depois do início.';
    else if (end - start > 12 * 3600 * 1000) invalid.ends_at = 'A reserva pode durar no máximo 12 horas.';
    if (Object.keys(invalid).length) { setFields(invalid); setError('Confira os campos destacados.'); return; }
    setPending(true);
    try {
      unwrap(await api.POST('/api/reservas', { body: { charger_id: Number(chargerId), connector: Number(connector), starts_at: startsAt, ends_at: endsAt } }));
      onCreated();
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 422 && Array.isArray(reason.detail)) {
        const invalidFields: Record<string, string> = {};
        for (const detail of reason.detail) {
          const key = Array.isArray(detail.loc) ? detail.loc.at(-1) : undefined;
          if (typeof key === 'string') invalidFields[key] = 'Confira este campo e tente novamente.';
        }
        setFields(invalidFields);
      }
      setError(reason instanceof ApiError && reason.status === 409 ? 'Esse horário já foi reservado. Confira a disponibilidade atualizada e escolha outra janela.' : errorMessage(reason));
      availability.retry();
    } finally { setPending(false); }
  }
  function described(key: string) { return fields[key] ? `${key}-error` : undefined; }
  if (!chargers.length) return <section className="card empty-state"><Icon name="plug" /><h2>Nenhum carregador disponível</h2><p>Não há carregadores ativos no cadastro do condomínio. Consulte o síndico.</p></section>;
  return <div className="reservation-grid"><section className="card"><div className="card-heading"><h2>Agendar recarga</h2><span className="tag">Até 12 horas</span></div><p className="muted small-text">Todos os horários seguem o fuso de São Paulo (UTC−03:00).</p>
    {user?.reservation_blocked_until && Date.parse(user.reservation_blocked_until) > Date.now() && <Alert>Reservas bloqueadas até {formatDate(user.reservation_blocked_until)}, {formatTime(user.reservation_blocked_until)}.</Alert>}
    {draft && <p className="draft-note">Horário sugerido preenchido. Confira o conector e confirme para agendar. Nada foi reservado ainda.</p>}
    {draft && !charger && <Alert>O carregador sugerido não está mais disponível. Escolha outro carregador.</Alert>}
    <form onSubmit={submit} aria-busy={pending}>
      <fieldset disabled={pending}><legend className="sr-only">Dados da reserva</legend>
        <label htmlFor="charger">Carregador</label><select id="charger" value={chargerId} onChange={event => { setChargerId(event.target.value); setConnector('1'); }} required aria-invalid={!!fields.charger_id} aria-describedby={described('charger_id')}>{chargers.map(item => <option key={item.id} value={item.id}>{item.code} · {item.location || item.model}</option>)}</select>{fields.charger_id && <p className="field-error" id="charger_id-error">{fields.charger_id}</p>}
        {charger && <p className="field-hint">{charger.model} · {charger.rated_power_kw.replace('.', ',')} kW nominais · {charger.connectors} {charger.connectors === 1 ? 'conector' : 'conectores'}</p>}
        <label htmlFor="connector">Conector</label><select id="connector" value={connector} onChange={event => setConnector(event.target.value)} aria-invalid={!!fields.connector} aria-describedby={described('connector')}>{Array.from({ length: charger?.connectors ?? 0 }, (_, i) => <option key={i} value={i + 1}>Conector {i + 1}</option>)}</select>{fields.connector && <p className="field-error" id="connector-error">{fields.connector}</p>}
        <div className="form-row"><div><label htmlFor="date">Data de início</label><input id="date" type="date" required min={condoDate()} value={date} onChange={event => { setDate(event.target.value); setEndDate(event.target.value); }} aria-invalid={!!fields.starts_at} aria-describedby={described('starts_at')} /></div><div><label htmlFor="start-time">Horário de início</label><input id="start-time" type="time" step="1" required value={startTime} onChange={event => setStartTime(event.target.value)} aria-invalid={!!fields.starts_at} aria-describedby={described('starts_at')} /></div></div>{fields.starts_at && <p className="field-error" id="starts_at-error">{fields.starts_at}</p>}
        <div className="form-row"><div><label htmlFor="end-date">Data de término</label><input id="end-date" type="date" required min={date} value={endDate} onChange={event => setEndDate(event.target.value)} aria-invalid={!!fields.ends_at} aria-describedby={described('ends_at')} /></div><div><label htmlFor="end-time">Horário de término</label><input id="end-time" type="time" step="1" required value={endTime} onChange={event => setEndTime(event.target.value)} aria-invalid={!!fields.ends_at} aria-describedby={described('ends_at')} /></div></div>{fields.ends_at && <p className="field-error" id="ends_at-error">{fields.ends_at}</p>}
      </fieldset>
      {error && <Alert>{error}</Alert>}<div className="form-actions"><button className="button primary" disabled={pending || !charger || availability.loading || !!availability.error || !date}>{pending ? 'Confirmando…' : 'Confirmar reserva'}<Icon name="arrow" /></button><p className="muted small-text">A reserva é confirmada após a verificação do horário.</p></div>
    </form>
  </section><aside className="card availability-card"><div className="card-heading"><h2>Horários ocupados</h2><Icon name="calendar" /></div><p className="muted small-text">{date ? formatDate(reservationTimestamp(date, '12:00')) : 'Escolha uma data'} · Conector {connector}</p>
    {availability.loading ? <p role="status">Consultando disponibilidade…</p> : availability.error ? <QueryError message={availability.error} retry={availability.retry} /> : availability.data && <>{busy.length ? <ul className="busy-list">{busy.map((item, index) => <li key={index}><span>Ocupado</span><strong>{formatDate(item.starts_at) === formatDate(item.ends_at) ? `${formatTime(item.starts_at)} – ${formatTime(item.ends_at)}` : `${formatDate(item.starts_at)}, ${formatTime(item.starts_at)} – ${formatDate(item.ends_at)}, ${formatTime(item.ends_at)}`}</strong></li>)}</ul> : <div className="availability-empty"><Icon name="calendar" /><strong>Nenhum horário ocupado</strong><p>Não há reservas para este conector na data consultada.</p></div>}<button className="button secondary small" onClick={availability.retry} disabled={pending}>Atualizar horários</button></>}
    <p className="availability-note">A disponibilidade pode mudar até a confirmação. A agenda não indica o estado físico do equipamento.</p>
  </aside></div>;
}

export function ReservationList({ chargers, residents }: { chargers: Charger[]; residents?: components['schemas']['UserOut'][] }) {
  const { api } = useAuth();
  const reservations = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/reservas', { signal })), [api]));
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const [error, setError] = useState(''); const [success, setSuccess] = useState('');
  const now = useTimeBoundaries((reservations.data ?? []).flatMap(row => [Date.parse(row.starts_at), Date.parse(row.ends_at)]));
  async function cancel(id: number) {
    if (pending !== null) return;
    const row = reservations.data?.find(item => item.id === id);
    if (!row || !canCancelReservation(row, Date.now())) {
      setError('Só é possível cancelar antes do início da reserva. Atualize a lista.');
      setConfirmId(null); reservations.retry(); return;
    }
    setPending(id); setError(''); setSuccess('');
    try { unwrap(await api.POST('/api/reservas/{reservation_id}/cancelar', { params: { path: { reservation_id: id } } })); setSuccess(`Reserva #${id} cancelada. O horário foi liberado.`); setConfirmId(null); reservations.retry(); }
    catch (reason) { setError(errorMessage(reason)); reservations.retry(); setConfirmId(null); }
    finally { setPending(null); }
  }
  const rows = orderedReservations(reservations.data ?? [], now);
  return <section className="card"><div className="card-heading"><h2>{residents ? 'Agenda do condomínio' : 'Seus agendamentos'}</h2><button className="button secondary small" onClick={reservations.retry} disabled={reservations.loading || pending !== null}>Atualizar lista</button></div>
    {error && <Alert>{error}</Alert>}{success && <Alert success>{success}</Alert>}
    {reservations.loading ? <p role="status">Carregando reservas…</p> : reservations.error ? <QueryError message={reservations.error} retry={reservations.retry} /> : !rows.length ? residents ? <p className="muted">Nenhuma reserva registrada no condomínio.</p> : <div className="empty-state"><Icon name="calendar" /><h3>Sua próxima recarga começa com uma reserva</h3><p className="muted">Você ainda não tem agendamentos.</p><a className="button primary" href="#nova-reserva">Criar primeira reserva<Icon name="arrow" /></a></div> : <ul className="reservation-list">{rows.map(row => <li key={row.id} className="reservation-item"><div className="reservation-main"><span className="reservation-icon"><Icon name="plug" /></span><div><strong>{chargers.find(charger => charger.id === row.charger_id)?.code ?? `Carregador #${row.charger_id}`} <span className="muted">· Conector {row.connector}</span></strong><p>{formatDate(row.starts_at)} · {formatTime(row.starts_at)} – {condoDate(new Date(row.starts_at)) !== condoDate(new Date(row.ends_at)) && `${formatDate(row.ends_at)}, `}{formatTime(row.ends_at)}</p><small>Reserva #{row.id}{residents && ` · ${residents.find(resident => resident.id === row.user_id)?.name ?? `Morador #${row.user_id}`}`}</small></div></div><div className="reservation-actions"><span className={`status status-${row.status}`}>{reservationTemporalLabel(row, now) ?? statusLabels[row.status]}</span>{reservationTemporalLabel(row, now) && <small className="muted">Estado registrado: ativa. Cancelamento indisponível após o início.</small>}{canCancelReservation(row, now) && (confirmId === row.id ? <div className="cancel-confirm"><span>Cancelar este horário?</span><button className="button danger small" onClick={() => cancel(row.id)} disabled={pending !== null}>{pending === row.id ? 'Cancelando…' : 'Sim, cancelar'}</button><button className="button secondary small" onClick={() => setConfirmId(null)} disabled={pending !== null}>Manter reserva</button></div> : <button className="text-button" onClick={() => { setConfirmId(row.id); setError(''); setSuccess(''); }} disabled={pending !== null} aria-label={`Cancelar reserva #${row.id}`}>Cancelar reserva</button>)}</div></li>)}</ul>}
    <p className="small-text muted">Horários de São Paulo (UTC−03:00). Somente reservas ativas, antes do início, podem ser canceladas.</p>
  </section>;
}

