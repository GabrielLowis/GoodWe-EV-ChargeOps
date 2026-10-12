import { useEffect, useState } from 'react';

// Atualiza no instante da próxima transição e ao voltar à aba, sem polling da API.
export function useTimeBoundaries(boundaries: number[]) {
  const [now, setNow] = useState(() => Date.now());
  const signature = boundaries.filter(Number.isFinite).join(',');
  useEffect(() => setNow(Date.now()), [signature]);
  useEffect(() => {
    const refresh = () => setNow(Date.now());
    const current = Date.now();
    const next = signature.split(',').map(Number).filter(value => value > current).sort((a, b) => a - b)[0];
    const timer = next === undefined ? undefined : window.setTimeout(refresh, Math.min(2_147_483_647, Math.max(1, next - current)));
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', refresh);
    return () => {
      if (timer !== undefined) window.clearTimeout(timer);
      window.removeEventListener('focus', refresh);
      document.removeEventListener('visibilitychange', refresh);
    };
  }, [signature, now]);
  return now;
}
