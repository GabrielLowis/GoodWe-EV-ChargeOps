import { useCallback, useState } from 'react';
import { unwrap } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { Alert, QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { condoDate, errorMessage, formatEnergy, formatMoney, formatPeriod, record } from '../utils/presentation';
import { invoiceClosingAt, invoicePeriod, isFutureInvoice, reportCount, reportMoney } from '../utils/finance';
import { useTimeBoundaries } from '../hooks/useTimeBoundaries';
import { InvoiceDetail } from './InvoicesPage';

export function FinancePage({ id, period, onPeriodChange }: { id?: number; period: string; onPeriodChange(value: string): void }) {
  return <><div className="page-heading"><p className="eyebrow">FATURAMENTO DO CONDOMÍNIO</p><h1>{id ? 'Detalhe da fatura' : 'Financeiro'}</h1><p className="muted">Consulte valores faturados, gere cálculos e confira cada parcela.</p></div>{id ? <InvoiceDetail id={id} backHref="#financeiro" backLabel="Voltar para o financeiro" administration /> : <FinanceOverview period={period} onPeriodChange={onPeriodChange} />}</>;
}

function FinanceOverview({ period, onPeriodChange }: { period: string; onPeriodChange(value: string): void }) {
  const { api } = useAuth();
  const selection = invoicePeriod(period);
  const now = useTimeBoundaries([Date.parse(invoiceClosingAt(condoDate().slice(0, 7)))]);
  const invoices = useQuery(useCallback(async (signal: AbortSignal) => {
    if (!invoicePeriod(period)) return [];
    const rows = unwrap(await api.GET('/api/faturas', { signal }));
    return rows.filter(invoice => invoice.period.slice(0, 7) === period);
  }, [api, period]));
  const report = useQuery(useCallback(async (signal: AbortSignal) => {
    const query = invoicePeriod(period);
    return query ? unwrap(await api.GET('/api/relatorios/arrecadacao', { signal, params: { query } })) : null;
  }, [api, period]));
  const users = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/usuarios', { signal })), [api]));
  const [confirm, setConfirm] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  function refresh() { invoices.retry(); report.retry(); users.retry(); }
  async function generate() {
    if (!selection || pending) return;
    setPending(true); setError(''); setNotice('');
    try {
      const result = unwrap(await api.POST('/api/faturas/gerar', { body: selection }));
      setNotice(`${result.length} fatura(s) retornada(s) para ${formatPeriod(period)}. Consulte a situação e as parcelas abaixo.`);
      refresh();
    } catch (reason) { setError(errorMessage(reason, 'Informe um mês válido entre 2000 e 2100.')); refresh(); }
    finally { setPending(false); setConfirm(false); }
  }
  return <><section className="card"><div className="card-heading"><h2>Período de faturamento</h2><button className="button secondary small" onClick={refresh} disabled={pending || invoices.loading || report.loading}>Atualizar consultas</button></div>
    <label className="filter-field" htmlFor="invoice-period">Mês e ano<input id="invoice-period" type="month" min="2000-01" max="2100-12" required value={period} disabled={pending} onChange={event => { onPeriodChange(event.target.value); setConfirm(false); setError(''); setNotice(''); }} /></label>
    {!selection && <Alert>Selecione um mês e ano entre 2000 e 2100.</Alert>}{error && <Alert>{error}</Alert>}{notice && <Alert success>{notice}</Alert>}
    <p className="muted small-text">A geração atende o conjunto de moradores elegíveis. Faturas abertas podem ser recalculadas; faturas fechadas mantêm o cálculo definitivo. Residentes ativos sem consumo podem receber fatura de valor zero.</p>
    {confirm ? <div className="financial-confirm"><p>Gerar/recalcular as faturas de <strong>{selection ? formatPeriod(period) : 'período inválido'}</strong>? Os cálculos abertos deste período serão atualizados pela API.</p><div className="action-row"><button className="button primary" disabled={pending} onClick={generate}>{pending ? 'Gerando…' : 'Confirmar geração'}</button><button className="button secondary" disabled={pending} onClick={() => setConfirm(false)}>Voltar sem gerar</button></div></div> : <button className="button primary" disabled={!selection || pending} onClick={() => { setConfirm(true); setError(''); setNotice(''); }}>Gerar / recalcular faturas</button>}
  </section>
    {selection && <><section className="card detail-section"><h2>Faturas de {formatPeriod(period)}</h2>{users.error && <QueryError message={users.error} retry={users.retry} />}{invoices.loading ? <p role="status">Carregando faturas…</p> : invoices.error ? <QueryError message={invoices.error} retry={invoices.retry} /> : !invoices.data?.length ? <p className="muted">Nenhuma fatura gerada para este período.</p> : <ul className="data-list">{invoices.data.map(invoice => <li key={invoice.id}><div><a className="item-title" href={`#financeiro/${invoice.id}`}>Fatura #{invoice.id} · {users.data?.find(user => user.id === invoice.user_id)?.name ?? `Morador #${invoice.user_id}`}</a><p>{isFutureInvoice(invoice.period, now) && <span className="tag">Período futuro</span>}{invoice.sessions_count} recarga(s) incluída(s) · <span className="tag">{invoice.status === 'open' ? 'Aberta' : 'Fechada'}</span></p></div><div className="list-end"><strong>{formatMoney(invoice.total)}</strong><a className="button secondary small" href={`#financeiro/${invoice.id}`}>Ver fatura #{invoice.id}</a></div></li>)}</ul>}</section>
    <section className="card detail-section"><h2>Resumo mensal do faturamento</h2>{report.loading ? <p role="status">Consultando relatório…</p> : report.error ? <QueryError message={report.error} retry={report.retry} /> : report.data && <ReportSummary data={report.data} />}</section></>}
    <p className="environment-note">Faturamento é o valor calculado nas faturas. O sistema não registra pagamentos nem dinheiro recebido.</p>
  </>;
}

export function ReportSummary({ data }: { data: Record<string, unknown> }) {
  const totals = record(data.totals), balance = record(data.energy_balance), reimbursement = record(data.condominium_reimbursement);
  const energy = (value: unknown) => typeof value === 'string' && /^\d+(\.\d+)?$/.test(value) ? formatEnergy(value) : 'Não informado';
  const buckets = { billed: 'Sessões faturadas', waiting_review: 'Aguardando revisão', rejected: 'Rejeitadas', unattributed: 'Sem morador identificado', approved_not_invoiced: 'Aprovadas sem fatura', system_failure_not_charged: 'Falha do sistema · sem cobrança' };
  return <><p className="muted small-text">{reportCount(totals.invoices_count)} fatura(s) · {reportCount(totals.closed_invoices)} fechada(s).</p>
    <div className="metric-grid"><div><span>Total faturado</span><strong>{reportMoney(totals.total)}</strong></div><div><span>Energia faturada</span><strong>{energy(totals.billed_kwh)}</strong></div><div><span>Energia registrada no mês</span><strong>{energy(balance.delivered_kwh)}</strong></div></div>
    <dl className="amount-list">{[['Energia Green', totals.green_amount], ['Energia Grid', totals.grid_amount], ['Ociosidade', totals.idle_amount], ['Subtotal', totals.subtotal], ['Impostos', totals.tax_amount], ['Custo operacional', totals.overhead_amount], ['Total faturado', totals.total]].map(([label, value]) => <div key={String(label)}><dt>{String(label)}</dt><dd>{reportMoney(value)}</dd></div>)}</dl>
    <h3>Distribuição dos valores faturados</h3><dl className="detail-list">{[['Energia destinada ao condomínio', reimbursement.energy_amount], ['Ociosidade', reimbursement.idle_amount], ['Custo operacional', reimbursement.overhead_amount], ['Impostos destacados', reimbursement.tax_to_collect]].map(([label, value]) => <div key={String(label)}><dt>{String(label)}</dt><dd>{reportMoney(value)}</dd></div>)}</dl>
    <h3 className="detail-section">Situação da energia registrada</h3><dl className="detail-list">{Object.entries(buckets).map(([key, label]) => { const bucket = record(balance[key]); return <div key={key}><dt>{label}</dt><dd>{reportCount(bucket.count)} sessão(ões) · {energy(bucket.kwh)}{Array.isArray(bucket.session_ids) && bucket.session_ids.length > 0 && <div className="report-links">{bucket.session_ids.filter((id): id is number => typeof id === 'number' && Number.isSafeInteger(id) && id > 0).map(id => <a key={id} href={`#sessoes/${id}`}>Sessão #{id}</a>)}</div>}</dd></div>; })}</dl>
    <p className="muted small-text">Lançamentos de meses anteriores: {reportCount(record(balance.late_entries_from_previous_periods).count)} · {reportMoney(record(balance.late_entries_from_previous_periods).amount)}. Energia faturada pode incluir esses lançamentos.</p>
    <p className="environment-note">{typeof data.scope === 'string' ? data.scope : 'Valores faturados; pagamentos e recebimentos não são registrados neste sistema.'}</p>
  </>;
}
