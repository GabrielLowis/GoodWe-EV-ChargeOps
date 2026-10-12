import type { ReactNode } from 'react';
import goodweLogo from '../assets/brand/goodwe.svg';

export function Icon({ name }: { name: 'bolt' | 'home' | 'calendar' | 'plus' | 'logout' | 'arrow' | 'plug' | 'receipt' | 'settings' | 'warning' | 'calendar-plus' | 'clock-energy' }) {
  const paths = {
    bolt: 'm13 2-9 12h7l-1 8 10-13h-7l0-7Z', home: 'm3 10 9-7 9 7M5 9v12h5v-7h4v7h5V9',
    calendar: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z',
    plus: 'M12 5v14M5 12h14', logout: 'M9 4H4v16h5m5-12 4 4-4 4m-5-4h12', arrow: 'M4 12h16m-6-6 6 6-6 6', plug: 'M9 3v5m6-5v5M6 8h12v4a6 6 0 0 1-12 0V8Zm6 10v4',
    receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 7h6M9 11h6M9 15h3',
    settings: 'M4 7h5m4 0h7M4 17h9m4 0h3M9 4v6m4 4v6M9 7h4m0 10h4',
    warning: 'M10.3 4.3 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0ZM12 9v5m0 3v.1',
    'calendar-plus': 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM12 13v6m-3-3h6',
    'clock-energy': 'M20 10a8 8 0 1 0-8 10M12 6v6l-3 2m9-2-4 6h4l-1 4 5-6h-4l1-4Z',
  };
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
export function Brand() { return <div className="brand"><span className="brand-signature"><img src={goodweLogo} width="128" height="19" alt="GoodWe" /></span><span className="brand-product">EV ChargeOps<small>GOODWE × FIAP</small></span></div>; }
export function Alert({ children, success = false }: { children: ReactNode; success?: boolean }) { return <div className={`alert ${success ? 'alert-success' : 'alert-error'}`} role={success ? 'status' : 'alert'}>{children}</div>; }
export function QueryError({ message, retry }: { message: string; retry(): void }) { return <Alert><p>{message}</p><button className="button secondary small" onClick={retry}>Tentar novamente</button></Alert>; }
