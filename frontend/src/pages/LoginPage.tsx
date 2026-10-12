import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { Alert, Brand, Icon } from '../components/ui';
import { errorMessage } from '../utils/presentation';
import hcaG2 from '../assets/images/goodwe-hca-g2.png';

export function LoginPage({ onLogin }: { onLogin(): void }) {
  const { login } = useAuth();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false); const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (pending) return;
    setError(''); setPending(true);
    try { await login(email.trim(), password); onLogin(); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 401 ? 'E-mail ou senha inválidos. Confira seus dados e tente novamente.' : errorMessage(reason)); }
    finally { setPending(false); }
  }
  return <main className="login-page">
    <section className="login-story" aria-label="EV ChargeOps"><Brand />
      <div className="story-content"><p className="eyebrow">RECARGA NO SEU CONDOMÍNIO</p><h1>Seu próximo trajeto<br />começa aqui.</h1><p>Reserve seu horário e organize a recarga com a praticidade que faz parte da sua rotina.</p>
        <div className="charge-illustration hca-product" aria-hidden="true"><img src={hcaG2} width="1020" height="1300" alt="" /><div className="illustration-caption">ENERGIA PARA SEGUIR</div></div>
      </div><p className="story-footer">GoodWe × FIAP <span>EV ChargeOps</span></p>
    </section>
    <section className="login-panel" aria-labelledby="login-title"><div className="login-form-wrapper"><p className="eyebrow">BEM-VINDO AO EV CHARGEOPS</p><h2 id="login-title">Acesse sua conta</h2><p className="muted">Entre com os dados fornecidos pelo condomínio.</p>
      <form onSubmit={submit} aria-busy={pending}>
        <label htmlFor="email">E-mail</label><input id="email" type="email" autoComplete="username" placeholder="voce@exemplo.com" required value={email} onChange={event => setEmail(event.target.value)} disabled={pending} aria-describedby={error ? 'login-error' : undefined} aria-invalid={error ? true : undefined} />
        <label htmlFor="password">Senha</label><div className="password-field"><input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Digite sua senha" required value={password} onChange={event => setPassword(event.target.value)} disabled={pending} aria-describedby={error ? 'login-error' : undefined} aria-invalid={error ? true : undefined} /><button type="button" className="button secondary small" aria-controls="password" aria-pressed={showPassword} disabled={pending} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Ocultar senha' : 'Mostrar senha'}</button></div>
        {error && <div id="login-error"><Alert>{error}</Alert></div>}<button className="button primary login-submit" disabled={pending}>{pending ? 'Entrando…' : 'Entrar na minha conta'}{!pending && <Icon name="arrow" />}</button>
      </form><p className="login-help">O acesso ao morador ou ao síndico é definido pela sua conta. Ao recarregar a página, entre novamente.</p>
    </div><p className="login-bottom">Gestão de recarga compartilhada</p></section>
  </main>;
}
