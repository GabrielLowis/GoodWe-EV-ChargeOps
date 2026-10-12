import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { unwrap } from '../api/client';
import type { components } from '../api/schema';
import { useAuth } from '../auth/AuthProvider';
import { Alert, Icon, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { errorMessage, formatDate, formatMoney, formatTime } from '../utils/presentation';
import type { ReservationDraft } from '../utils/presentation';

export function RecommendationPage({ onUse }: { onUse(draft: ReservationDraft): void }) {
  const { api } = useAuth();
  const chargers = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/carregadores', { signal })), [api]));
  return <><div className="page-heading"><p className="eyebrow">PLANEJE SUA PRÓXIMA RECARGA</p><h1>Sugestão de horário</h1><p className="muted">Compare uma janela sugerida com a estimativa de recarregar agora.</p></div>
    {chargers.loading ? <section className="card" role="status">Carregando carregadores…</section> : chargers.error ? <QueryError message={chargers.error} retry={chargers.retry} /> : chargers.data && <RecommendationForm chargers={chargers.data.filter(item => item.active)} onUse={onUse} />}
  </>;
}
function RecommendationForm({ chargers, onUse }: { chargers: components['schemas']['ChargerOut'][]; onUse(draft: ReservationDraft): void }) {
  const { api } = useAuth();
  const [chargerId, setChargerId] = useState(String(chargers[0]?.id ?? ''));
  const initialPower = (id: string) => String(Math.min(3.3, Number(chargers.find(item => item.id === Number(id))?.rated_power_kw ?? 3.3)));
  const [kwh, setKwh] = useState(''); const [power, setPower] = useState(() => initialPower(chargerId));
  const [result, setResult] = useState<components['schemas']['RecommendationOut']>();
  const [pending, setPending] = useState(false); const [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const charger = chargers.find(item => item.id === Number(chargerId));
  function clear() { setResult(undefined); setError(''); }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (pending) return;
    clear(); setPending(true);
    const controller = new AbortController(); request.current = controller;
    try {
      const response = unwrap(await api.GET('/api/recomendacao-janela', { signal: controller.signal, params: { query: { charger_id: Number(chargerId), kwh, power_kw: power } } }));
      if (!controller.signal.aborted) setResult(response);
    } catch (reason) { if (!controller.signal.aborted) setError(errorMessage(reason, 'Confira a energia (até 200 kWh), a potência e os limites do carregador.')); }
    finally { if (!controller.signal.aborted) setPending(false); }
  }
  if (!chargers.length) return <section className="card"><h2>Nenhum carregador disponível</h2><p className="muted">Não há carregadores ativos para consultar uma sugestão.</p></section>;
  return <div className="reservation-grid"><section className="card"><h2>Dados da recarga</h2><form id="suggest-form" onSubmit={submit} aria-busy={pending}><fieldset disabled={pending}><legend className="sr-only">Parâmetros da sugestão</legend>
    <label htmlFor="suggest-charger">Carregador</label><select id="suggest-charger" value={chargerId} onChange={event => { setChargerId(event.target.value); setPower(initialPower(event.target.value)); clear(); }}>{chargers.map(item => <option value={item.id} key={item.id}>{item.code} · {item.location || item.model}</option>)}</select>
    <label htmlFor="suggest-kwh">Energia desejada (kWh)</label><input id="suggest-kwh" type="number" required min="0.001" max="200" step="0.001" placeholder="Ex.: 7" value={kwh} onChange={event => { setKwh(event.target.value); clear(); }} />
    <label htmlFor="suggest-power">Potência estimada (kW)</label><input id="suggest-power" type="number" required min="0.01" max={Math.min(22, Number(charger?.rated_power_kw ?? 22))} step="0.01" value={power} onChange={event => { setPower(event.target.value); clear(); }} aria-describedby="power-hint" /><p id="power-hint" className="field-hint">Até {Math.min(22, Number(charger?.rated_power_kw ?? 22)).toLocaleString('pt-BR')} kW neste carregador. A janela estimada deve caber em 12 horas.</p>
    </fieldset><div className="form-actions"><button className="button primary" disabled={pending}>{pending ? 'Consultando…' : 'Consultar sugestão'}<Icon name="arrow" /></button></div></form>{error && <Alert><p>{error}</p><button className="button secondary small" type="submit" form="suggest-form" disabled={pending}>Tentar novamente</button></Alert>}
  </section><section className="card"><h2>{result ? 'Horário sugerido' : 'Uma estimativa para planejar'}</h2>
    {!result ? <p className="muted">Informe os dados para consultar uma janela nas próximas 24 horas. A estimativa utiliza geração solar hipotética, sem previsão meteorológica.</p> : <>
      <span className="tag">Estimativa · geração solar hipotética</span><p className="suggested-window">{formatDate(result.recommended_start)}<strong>{formatTime(result.recommended_start)} – {formatDate(result.recommended_start) !== formatDate(result.recommended_end) && `${formatDate(result.recommended_end)}, `}{formatTime(result.recommended_end)}</strong><small>Horários de São Paulo</small></p>
      <dl className="amount-list"><div><dt>Custo estimado na sugestão</dt><dd>{formatMoney(result.predicted_cost)}</dd></div><div><dt>Custo estimado agora</dt><dd>{formatMoney(result.cost_if_now)}</dd></div><div><dt>Economia estimada</dt><dd>{formatMoney(result.savings)}</dd></div></dl>
      <h3>Premissas da estimativa</h3><ul className="explanation-list">{result.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul>
      <button className="button primary" onClick={() => onUse({ charger_id: Number(chargerId), starts_at: result.recommended_start, ends_at: result.recommended_end })}>Usar este horário<Icon name="arrow" /></button><p className="environment-note">Você ainda precisa escolher/conferir o conector e confirmar a reserva. A disponibilidade pode mudar.</p>
    </>}
  </section></div>;
}

