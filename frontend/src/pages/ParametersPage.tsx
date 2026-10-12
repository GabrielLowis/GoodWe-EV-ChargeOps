import { useCallback } from 'react';
import type { ReactNode } from 'react';
import { unwrap } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { QueryError } from '../components/ui';
import { useQuery } from '../hooks/useQuery';
import { formatDate, formatTime } from '../utils/presentation';
import { formatUnitPrice } from '../utils/finance';

const bands: Record<string, string> = { off_peak: 'Fora de ponta', intermediate: 'Intermediária', peak: 'Ponta' };
function validity(start: string, end: string | null) { return `${formatDate(start)}, ${formatTime(start)} até ${end ? `${formatDate(end)}, ${formatTime(end)} (fim exclusivo)` : 'sem término cadastrado'}`; }
function ParameterSection({ title, query, empty, children }: { title: string; query: { loading: boolean; error: string; retry(): void }; empty: boolean; children: ReactNode }) {
  return <section className="card detail-section"><div className="card-heading"><h2>{title}</h2><button className="button secondary small" disabled={query.loading} onClick={query.retry}>Atualizar {title.toLowerCase()}</button></div>{query.loading ? <p role="status">Consultando {title.toLowerCase()}…</p> : query.error ? <QueryError message={query.error} retry={query.retry} /> : empty ? <p className="muted">Nenhum registro disponível.</p> : children}</section>;
}

export function ParametersPage() {
  const { api } = useAuth();
  const chargers = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/carregadores', { signal })), [api]));
  const units = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/unidades', { signal })), [api]));
  const tariffs = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/tarifas', { signal })), [api]));
  const taxes = useQuery(useCallback(async (signal: AbortSignal) => unwrap(await api.GET('/api/impostos', { signal })), [api]));
  return <><div className="page-heading"><p className="eyebrow">BASE DA OPERAÇÃO</p><h1>Cadastros e parâmetros</h1><p className="muted">Consulte os equipamentos, unidades e regras cadastradas para o faturamento.</p></div>
    <ParameterSection title="Carregadores" query={chargers} empty={!chargers.data?.length}>{chargers.data?.map(charger => <article className="parameter-item" key={charger.id}><h3>{charger.code} · {charger.model}</h3><dl className="detail-list"><div><dt>Cadastro</dt><dd>{charger.active ? 'Ativo' : 'Inativo'}</dd></div><div><dt>Potência / conectores</dt><dd>{charger.rated_power_kw.replace('.', ',')} kW · {charger.connectors} conector(es)</dd></div><div><dt>Localização</dt><dd>{charger.location ?? 'Não informada'}</dd></div><div><dt>Número de série</dt><dd>{charger.serial_number}</dd></div><div><dt>Telemetria</dt><dd>Indisponível · sem estado físico online</dd></div></dl></article>)}</ParameterSection>
    <ParameterSection title="Unidades" query={units} empty={!units.data?.length}><ul className="data-list">{units.data?.map(unit => <li key={unit.id}><div><strong>{unit.label}</strong><p>Bloco {unit.block || 'não informado'} · Unidade {unit.number}</p></div></li>)}</ul></ParameterSection>
    <ParameterSection title="Tarifas" query={tariffs} empty={!tariffs.data?.length}>{tariffs.data?.map(tariff => <article className="parameter-item" key={tariff.id}><h3>{tariff.name} · Versão #{tariff.id}</h3><p className="small-text muted">Vigência: {validity(tariff.valid_from, tariff.valid_to)}.</p><dl className="detail-list">{tariff.bands.map(band => <div key={band.band}><dt>{bands[band.band]}</dt><dd>Green {formatUnitPrice(band.green_price_per_kwh)} / kWh<br />Grid {formatUnitPrice(band.grid_price_per_kwh)} / kWh</dd></div>)}<div><dt>Ociosidade</dt><dd>Tolerância de {tariff.idle_tolerance_minutes} min · {formatUnitPrice(tariff.idle_fee_per_minute)} / min</dd></div><div><dt>Custo operacional</dt><dd>{tariff.overhead_percent.replace('.', ',')}%</dd></div><div><dt>Fins de semana e feriados cadastrados</dt><dd>{tariff.weekends_holidays_off_peak ? 'Fora de ponta' : 'Seguem as janelas cadastradas'}</dd></div><div><dt>Referência da assembleia</dt><dd>{tariff.assembly_reference ?? 'Não informada'}</dd></div></dl><h4>Janelas de dias úteis</h4>{tariff.windows?.length ? <ul className="explanation-list">{tariff.windows.map((window, index) => <li key={index}>{bands[window.band]} · {window.start_time.slice(0, 5)}–{window.end_time.slice(0, 5)} (São Paulo)</li>)}</ul> : <p className="small-text muted">Nenhuma janela especial cadastrada.</p>}</article>)}</ParameterSection>
    <ParameterSection title="Impostos" query={taxes} empty={!taxes.data?.length}>{taxes.data?.map(tax => <article className="parameter-item" key={tax.id}><h3>{tax.tax_type.toUpperCase()} · Versão #{tax.id}</h3><dl className="detail-list"><div><dt>Jurisdição</dt><dd>{tax.jurisdiction}</dd></div><div><dt>Alíquota</dt><dd>{tax.rate_percent.replace('.', ',')}%</dd></div><div><dt>Vigência</dt><dd>{validity(tax.valid_from, tax.valid_to)}</dd></div><div><dt>Energia compensada</dt><dd>{tax.exclude_compensated_energy ? 'Excluída da base de cálculo' : 'Sem exclusão da base de cálculo'}</dd></div><div><dt>Base legal / observação</dt><dd>{tax.legal_basis ?? 'Não informada'}</dd></div></dl></article>)}</ParameterSection>
    <p className="environment-note">Horários de São Paulo. O tratamento de feriados depende das datas cadastradas no calendário. A configuração demonstrativa não representa um calendário real completo. Os parâmetros são os cadastrados na API; valores de demonstração não comprovam uma regra tributária real.</p>
  </>;
}
