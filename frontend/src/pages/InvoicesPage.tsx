import { useCallback, useState } from 'react';
import { unwrap } from '../api/client';
import type { components } from '../api/schema';
import { useAuth } from '../auth/AuthProvider';
import { Alert, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { condoDate, errorMessage, formatDate, formatEnergy, formatMoney, formatPeriod, record, textList } from '../utils/presentation';
import { useTimeBoundaries } from '../hooks/useTimeBoundaries';
import { invoiceClosingAt, isFutureInvoice } from '../utils/finance';

type Invoice = components['schemas']['InvoiceOut'];
type Item = components['schemas']['InvoiceItemOut'];
function Amounts({ data }: { data: Invoice | Item }) {
  const amounts = [['Energia Green · solar/bateria', data.green_amount], ['Energia Grid · rede elétrica', data.grid_amount], ['Ociosidade', data.idle_amount], ['Subtotal', data.subtotal], ['Impostos', data.tax_amount], ['Custo operacional', data.overhead_amount], ['Total', data.total]];
  return <dl className="amount-list">{amounts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{formatMoney(value)}</dd></div>)}</dl>;
}
function Notes({ value }: { value: unknown }) {
  const notes = textList(value);
  return notes.length ? <ul className="explanation-list">{notes.map((note, index) => <li key={index}>{note}</li>)}</ul> : <p className="muted small-text">Sem observações adicionais.</p>;
}
export function InvoicesPage({ id }: { id?: number }) {
  return <><div className="page-heading"><p className="eyebrow">SEU USO, COM TRANSPARÊNCIA</p><h1>{id ? 'Detalhe da fatura' : 'Minhas faturas'}</h1><p className="muted">Consulte os valores faturados e entenda cada parcela.</p></div>{id ? <InvoiceDetail id={id} /> : <InvoiceList />}</>;
}
function InvoiceList() {
  const { api } = useAuth();
  const invoices = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/faturas', { signal })), [api]));
  const now = useTimeBoundaries([Date.parse(invoiceClosingAt(condoDate().slice(0, 7)))]);
  return <section className="card"><div className="card-heading"><h2>Faturas mensais</h2><button className="button secondary small" disabled={invoices.loading} onClick={invoices.retry}>Atualizar lista</button></div>
    {invoices.loading ? <p role="status">Carregando faturas…</p> : invoices.error ? <QueryError message={invoices.error} retry={invoices.retry} /> : !invoices.data?.length ? <p className="muted">Nenhuma fatura disponível para sua conta.</p> : <ul className="data-list">{[...invoices.data].sort((a, b) => b.period.localeCompare(a.period)).map(invoice => <li key={invoice.id}><div><a className="item-title" href={`#faturas/${invoice.id}`}>{formatPeriod(invoice.period)}</a>{isFutureInvoice(invoice.period, now) && <span className="tag">Período futuro</span>}<p>{invoice.sessions_count} {invoice.sessions_count === 1 ? 'recarga incluída' : 'recargas incluídas'} · <span className="tag">{invoice.status === 'open' ? 'Aberta' : 'Fechada'}</span></p></div><div className="list-end"><strong>{formatMoney(invoice.total)}</strong><a className="button secondary small" href={`#faturas/${invoice.id}`}>Ver fatura #{invoice.id}</a></div></li>)}</ul>}
    <p className="environment-note">Aberta ou fechada indica a situação do cálculo. Pagamentos não são registrados neste sistema.</p>
  </section>;
}
export function InvoiceDetail({ id, backHref = '#faturas', backLabel = 'Voltar para minhas faturas', administration = false }: { id: number; backHref?: string; backLabel?: string; administration?: boolean }) {
  const { api, user } = useAuth();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const invoice = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/faturas/{invoice_id}', { signal, params: { path: { invoice_id: id } } })), [api, id]));
  const now = useTimeBoundaries([Date.parse(invoiceClosingAt(condoDate().slice(0, 7)))]);
  const data = invoice.data;
  return <><a className="back-link" href={backHref}>← {backLabel}</a>
    {notice && <Alert success>{notice}</Alert>}{error && <Alert>{error}</Alert>}
    {invoice.loading ? <section className="card" role="status">Carregando fatura…</section> : invoice.error ? <QueryError message={invoice.error} retry={invoice.retry} /> : data && <>
      <section className="card"><div className="card-heading"><h2>{formatPeriod(data.period)}</h2>{isFutureInvoice(data.period, now) && <span className="tag">Período futuro</span>}<span className="tag">{data.status === 'open' ? 'Aberta' : 'Fechada'}</span></div><div className="metric-grid"><div><span>Total faturado</span><strong>{formatMoney(data.total)}</strong></div><div><span>Green</span><strong>{formatEnergy(data.green_kwh)}</strong></div><div><span>Grid</span><strong>{formatEnergy(data.grid_kwh)}</strong></div></div><Amounts data={data} /><p className="muted small-text">{data.sessions_count} recarga(s) incluída(s) · {data.idle_minutes} min de ociosidade faturada.</p><p className="environment-note">{data.status === 'open' ? 'Fatura aberta: o cálculo ainda pode ser atualizado pelo síndico.' : 'Fatura fechada: o cálculo não pode ser atualizado.'} Esta situação não comprova pagamento.</p></section>
      <section className="card detail-section"><h2>Memória de cálculo</h2>{typeof data.calculation.formula === 'string' && <p className="muted small-text">{data.calculation.formula}</p>}<Notes value={data.calculation.notes} />
        {!data.items.length ? <p className="muted">Esta fatura não contém recargas.</p> : data.items.map(item => <InvoiceItem key={item.id} item={item} sessionHref={administration && user?.role === 'manager' ? '#sessoes' : '#recargas'} />)}
      </section>
      {Array.isArray(data.calculation.not_included) && data.calculation.not_included.length > 0 && <section className="card detail-section"><h2>Recargas não incluídas</h2><ul className="explanation-list">{data.calculation.not_included.map((value, index) => { const skipped = record(value); return <li key={index}>Recarga {typeof skipped.session_id === 'number' ? `#${skipped.session_id}` : 'não identificada'} — {typeof skipped.reason === 'string' ? skipped.reason : 'Motivo não informado'}</li>; })}</ul></section>}
      {administration && user?.role === 'manager' && <section className="card detail-section"><h2>Fechamento da fatura</h2><p className="small-text muted">Morador: {typeof record(data.calculation.user).name === 'string' ? String(record(data.calculation.user).name) : `#${data.user_id}`} · Fatura #{data.id}.</p>{data.status === 'closed' ? <p className="draft-note">Esta fatura está fechada. Não pode ser recalculada. Fechamento não registra pagamento.</p> : <InvoiceClosing data={data} onResult={(message, failed) => { setError(failed ? message : ''); setNotice(failed ? '' : message); invoice.retry(); }} />}</section>}
    </>}
  </>;
}
function InvoiceItem({ item, sessionHref = '#recargas' }: { item: Item; sessionHref?: string }) {
  const calculation = item.calculation;
  const rule = record(calculation.rule), tariff = record(calculation.tariff), split = record(calculation.band_split), components = record(calculation.components);
  const explanations = textList(calculation.explanation);
  const taxes = Array.isArray(components.taxes) ? components.taxes : [];
  return <details className="invoice-item"><summary><span>Recarga #{item.session_id}{item.is_late_entry && <span className="tag">Lançamento posterior</span>}</span><strong>{formatMoney(item.total)}</strong></summary><div className="invoice-item-content">
    <p><a href={`${sessionHref}/${item.session_id}`}>Ver dados da recarga #{item.session_id}</a></p>
    <p className="small-text">{typeof rule.description === 'string' ? rule.description : 'Descrição da regra não informada.'}</p>
    <Amounts data={item} />
    <p className="muted small-text">{formatEnergy(item.green_kwh)} Green · {formatEnergy(item.grid_kwh)} Grid · {item.idle_minutes} min de ociosidade.</p>
    {typeof tariff.name === 'string' && <p className="small-text">Tarifa utilizada: {tariff.name}.</p>}
    {typeof split.method_description === 'string' && <p className="small-text muted">{split.method_description}</p>}
    {explanations.length > 0 && <><h3>Como o valor foi calculado</h3><ul className="explanation-list">{explanations.map((line, index) => <li key={index}>{line}</li>)}</ul></>}
    {taxes.map((value, index) => { const tax = record(value); return typeof tax.legal_basis === 'string' ? <p className="small-text muted" key={index}>{typeof tax.label === 'string' ? `${tax.label}: ` : ''}{tax.legal_basis}</p> : null; })}
    <h3>Observações da recarga</h3><Notes value={calculation.notes} />
  </div></details>;
}

function InvoiceClosing({ data, onResult }: { data: Invoice; onResult(message: string, failed?: boolean): void }) {
  const { api } = useAuth();
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);
  const closingAt = invoiceClosingAt(data.period);
  const now = useTimeBoundaries([Date.parse(closingAt)]);
  const eligible = now >= Date.parse(closingAt);
  async function close() {
    if (pending) return;
    if (Date.now() < Date.parse(closingAt)) {
      setConfirm(false); onResult(`Fechamento disponível a partir de ${formatDate(closingAt)}, 00:00 (São Paulo).`, true); return;
    }
    setPending(true);
    try {
      unwrap(await api.POST('/api/faturas/{invoice_id}/fechar', { params: { path: { invoice_id: data.id } } }));
      onResult(`Fatura #${data.id} fechada. Seu cálculo foi preservado e não poderá ser atualizado.`);
    } catch (reason) { onResult(errorMessage(reason), true); }
    finally { setPending(false); }
  }
  if (!eligible) return <><p className="draft-note">Fechamento disponível a partir de {formatDate(closingAt)}, 00:00 (São Paulo), após o término do período. A fatura permanece aberta para atualização.</p><button className="button secondary" disabled>Fechar fatura #{data.id}</button></>;
  return confirm ? <div className="financial-confirm"><p>Fechar a fatura #{data.id} de <strong>{formatPeriod(data.period)}</strong>, no total de <strong>{formatMoney(data.total)}</strong>? Depois do fechamento, ela não poderá ser recalculada.</p><div className="action-row"><button className="button primary" disabled={pending} onClick={close}>{pending ? 'Fechando…' : 'Confirmar fechamento'}</button><button className="button secondary" disabled={pending} onClick={() => setConfirm(false)}>Manter aberta</button></div></div> : <><p className="muted small-text">Confira as parcelas e a memória de cálculo antes de fechar. O fechamento torna este cálculo definitivo.</p><button className="button secondary" onClick={() => setConfirm(true)}>Fechar fatura #{data.id}</button></>;
}
