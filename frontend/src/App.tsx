import { useEffect, useState } from 'react';
import { useAuth } from './auth/AuthProvider';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { ReservationsPage } from './pages/ReservationsPage';
import { Brand, Icon } from './components/ui';
import { SessionsPage } from './pages/SessionsPage';
import { InvoicesPage } from './pages/InvoicesPage';
import { RecommendationPage } from './pages/RecommendationPage';
import { ManagerAgenda, ManagerOverview, ManagerSessions } from './pages/ManagerPage';
import { AnomaliesPage } from './pages/AnomaliesPage';
import { FinancePage } from './pages/FinancePage';
import { ParametersPage } from './pages/ParametersPage';
import { condoDate } from './utils/presentation';
import type { ReservationDraft } from './utils/presentation';

type Page = 'financeiro' | 'parametros' | `financeiro/${number}` | 'agenda' | 'sessoes' | 'anomalias' | `sessoes/${number}` | `anomalias/${number}` | 'inicio' | 'nova-reserva' | 'reservas' | 'recargas' | 'faturas' | 'sugestao' | `recargas/${number}` | `faturas/${number}`;
function currentPage(): Page {
  const hash = window.location.hash.slice(1);
  if (['financeiro', 'parametros', 'agenda', 'sessoes', 'anomalias', 'nova-reserva', 'reservas', 'recargas', 'faturas', 'sugestao'].includes(hash)) return hash as Page;
  if (/^(recargas|faturas|sessoes|anomalias|financeiro)\/[1-9]\d*$/.test(hash) && Number.isSafeInteger(Number(hash.split('/')[1]))) return hash as Page;
  return 'inicio';
}

export function App() {
  const { user, logout } = useAuth();
  const [page, setPage] = useState<Page>(currentPage);
  const [notice, setNotice] = useState('');
  const [draft, setDraft] = useState<ReservationDraft>();
  const [financePeriod, setFinancePeriod] = useState(() => condoDate().slice(0, 7));
  useEffect(() => {
    const change = () => setPage(currentPage());
    window.addEventListener('hashchange', change);
    return () => window.removeEventListener('hashchange', change);
  }, []);
  useEffect(() => {
    if (user) document.getElementById('main-content')?.focus();
  }, [page, user?.id]);
  if (!user) return <LoginPage onLogin={() => { window.location.hash = 'inicio'; setPage('inicio'); setNotice(''); setDraft(undefined); }} />;
  const manager = user.role === 'manager';
  const adminPage = ['agenda', 'sessoes', 'anomalias', 'financeiro', 'parametros'].includes(page.split('/')[0]);
  const activePage = (manager ? page === 'inicio' || adminPage : !adminPage) ? page : 'inicio';
  const section = activePage.split('/')[0];
  const detailId = activePage.includes('/') ? Number(activePage.split('/')[1]) : undefined;
  const title = ({ financeiro: 'Financeiro', parametros: 'Cadastros e parâmetros', agenda: 'Agenda do condomínio', sessoes: 'Sessões do condomínio', anomalias: 'Fila de anomalias', 'nova-reserva': 'Nova reserva', reservas: 'Minhas reservas', recargas: 'Minhas recargas', faturas: 'Minhas faturas', sugestao: 'Sugestão de horário' } as Record<string, string>)[section] ?? (manager ? 'Visão geral' : 'Meu condomínio');
  function navigate(next: Page, message = '') { window.location.hash = next; setPage(next); setNotice(message); setDraft(undefined); }
  let content;
  if (section === 'inicio') content = manager ? <ManagerOverview /> : <HomePage onNavigate={navigate} />;
  else if (section === 'financeiro') content = <FinancePage id={detailId} period={financePeriod} onPeriodChange={setFinancePeriod} />;
  else if (section === 'parametros') content = <ParametersPage />;
  else if (section === 'agenda') content = <ManagerAgenda />;
  else if (section === 'sessoes') content = <ManagerSessions id={detailId} />;
  else if (section === 'anomalias') content = <AnomaliesPage id={detailId} />;
  else if (section === 'recargas') content = <SessionsPage id={detailId} />;
  else if (section === 'faturas') content = <InvoicesPage id={detailId} />;
  else if (section === 'sugestao') content = <RecommendationPage onUse={value => { navigate('nova-reserva'); setDraft(value); }} />;
  else content = <ReservationsPage mode={section === 'nova-reserva' ? 'create' : 'list'} draft={draft} notice={notice} onCreated={() => navigate('reservas', 'Reserva criada com sucesso. Seu horário está agendado.')} />;
  return <div className="app-shell">
    <a className="skip-link" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Pular para o conteúdo</a>
    <aside className="sidebar">
      <Brand /><div className="workspace-label">{manager ? 'Área do síndico' : 'Área do morador'}</div>
      <nav aria-label="Menu principal">
        <a href="#inicio" aria-current={activePage === 'inicio' ? 'page' : undefined} onClick={() => setNotice('')}><Icon name="home" />{manager ? 'Visão geral' : 'Início'}</a>
        {manager && <><a href="#agenda" aria-current={section === 'agenda' ? 'page' : undefined}><Icon name="calendar" />Agenda</a><a href="#sessoes" aria-current={section === 'sessoes' ? 'page' : undefined}><Icon name="plug" />Sessões</a><a href="#anomalias" aria-current={section === 'anomalias' ? 'page' : undefined}><Icon name="warning" />Anomalias</a><a href="#financeiro" aria-current={section === 'financeiro' ? 'page' : undefined}><Icon name="receipt" />Financeiro</a><a href="#parametros" aria-current={section === 'parametros' ? 'page' : undefined}><Icon name="settings" />Cadastros e parâmetros</a></>}
        {!manager && <><a href="#nova-reserva" aria-current={activePage === 'nova-reserva' ? 'page' : undefined} onClick={() => { setNotice(''); setDraft(undefined); }}><Icon name="calendar-plus" />Nova reserva</a><a href="#reservas" aria-current={activePage === 'reservas' ? 'page' : undefined} onClick={() => setNotice('')}><Icon name="calendar" />Minhas reservas</a><a href="#recargas" aria-current={section === 'recargas' ? 'page' : undefined} onClick={() => setNotice('')}><Icon name="plug" />Minhas recargas</a><a href="#faturas" aria-current={section === 'faturas' ? 'page' : undefined} onClick={() => setNotice('')}><Icon name="receipt" />Minhas faturas</a><a href="#sugestao" aria-current={section === 'sugestao' ? 'page' : undefined} onClick={() => setNotice('')}><Icon name="clock-energy" />Sugestão de horário</a></>}
      </nav>
      <div className="sidebar-note"><Icon name="bolt" /><p>Recarga compartilhada.<br />Organização para todos.</p></div>
      <div className="account"><div className="avatar" aria-hidden="true">{user.name.slice(0, 1).toUpperCase()}</div><div><strong>{user.name}</strong><span>{manager ? 'Síndico' : 'Morador'}</span></div></div>
      <button className="logout" onClick={() => { setDraft(undefined); logout(); }}><Icon name="logout" />Sair da conta</button>
    </aside>
    <div className="workspace"><header className="topbar"><span>Condomínio <span aria-hidden="true">/</span> <strong>{title}</strong></span><span className="profile-pill">{manager ? 'Síndico' : 'Morador'}</span></header>
      <main id="main-content" tabIndex={-1} key={activePage}>{content}</main>
      <footer className="workspace-footer">EV ChargeOps <span>GoodWe × FIAP · Projeto acadêmico</span></footer>
    </div>
  </div>;
}
