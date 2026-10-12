import { createContext, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createApiClient, unwrap } from '../api/client';
import type { ApiClient } from '../api/client';
import type { components } from '../api/schema';

type User = components['schemas']['UserOut'];
type Auth = { user: User | null; api: ApiClient; login(email: string, password: string): Promise<User>; logout(): void };
const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Token somente em memória; recarregar a página requer autenticar novamente.
  const token = useRef<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const logout = () => { token.current = null; setUser(null); };
  const [api] = useState(() => createApiClient({ token: () => token.current, onUnauthorized: logout }));
  async function login(email: string, password: string) {
    logout();
    try {
      const session = unwrap(await api.POST('/api/login', { body: { email, password } }));
      token.current = session.access_token;
      const current = unwrap(await api.GET('/api/usuarios/eu'));
      setUser(current);
      return current;
    } catch (error) { logout(); throw error; }
  }
  return <AuthContext.Provider value={{ user, api, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth requer AuthProvider');
  return auth;
}

export function RequireRole({ role, children }: { role?: User['role']; children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <p role="status">Autenticação necessária.</p>;
  if (role && user.role !== role) return <p role="alert">Acesso restrito a este perfil.</p>;
  return <>{children}</>;
}
