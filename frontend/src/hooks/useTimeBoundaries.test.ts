import { afterEach, describe, expect, it, vi } from 'vitest';
import { useTimeBoundaries } from './useTimeBoundaries';

const harness = vi.hoisted(() => ({ effects: [] as Array<() => void | (() => void)>, update: vi.fn() }));
vi.mock('react', () => ({ useState: (initial: () => number) => [initial(), harness.update], useEffect: (effect: () => void | (() => void)) => harness.effects.push(effect) }));

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); harness.effects = []; harness.update.mockClear(); });
describe('agendamento dos limites temporais sem recarregar', () => {
  it('atualiza exatamente no início, ao retomar a aba, e remove o timer/eventos', () => {
    vi.useFakeTimers(); vi.setSystemTime(1000);
    const events = new Map<string, () => void>();
    const remove = vi.fn();
    vi.stubGlobal('window', { setTimeout, clearTimeout, addEventListener: (name: string, cb: () => void) => events.set(name, cb), removeEventListener: remove });
    vi.stubGlobal('document', { addEventListener: (name: string, cb: () => void) => events.set(name, cb), removeEventListener: remove });
    expect(useTimeBoundaries([2000, 3000])).toBe(1000);
    const cleanup = harness.effects[1]();
    vi.advanceTimersByTime(999); expect(harness.update).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1); expect(harness.update).toHaveBeenLastCalledWith(2000);
    vi.setSystemTime(3500); events.get('visibilitychange')!(); expect(harness.update).toHaveBeenLastCalledWith(3500);
    if (typeof cleanup === 'function') cleanup();
    expect(remove).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
  });
});
