import { describe, expect, it } from 'vitest';
import { fmt, num } from './fmt';

describe('fmt', () => {
  it('renders mean, interval and unit with Western digits', () => {
    expect(fmt({ mean: 244.1, lo: 100.6, hi: 408.6 }, 'm³/day/h', 'Hypothesis')).toBe('244.1 (100.6–408.6) m³/day/h');
  });
  it('uses two decimals for probabilities', () => {
    expect(fmt({ mean: 0.82, lo: 0.47, hi: 0.98 }, '', 'Hypothesis')).toBe('0.82 (0.47–0.98)');
  });
  it('never emits Arabic-Indic digits', () => {
    const s = fmt({ mean: 1234.5, lo: 1000, hi: 1500 }, 'm³/day', 'Observed');
    expect(s).not.toMatch(/[٠-٩۰-۹]/);
    expect(num(7, 0)).toBe('7');
  });
  it('refuses a value without lo/hi', () => {
    expect(() => fmt({ mean: 244.1 } as never, 'm³/day/h', 'Hypothesis')).toThrow(/without mean, lo and hi/);
    expect(() => fmt({ mean: 244.1, lo: 100.6 } as never, 'm³/day/h', 'Hypothesis')).toThrow();
    expect(() => fmt(null, 'm³/day/h', 'Hypothesis')).toThrow();
    expect(() => fmt({ mean: NaN, lo: 1, hi: 2 }, '', 'Hypothesis')).toThrow();
  });
  it('refuses a value without an evidence label', () => {
    expect(() => fmt({ mean: 1, lo: 0.5, hi: 2 }, 'x', undefined)).toThrow(/evidence label/);
    expect(() => fmt({ mean: 1, lo: 0.5, hi: 2 }, 'x', '')).toThrow(/evidence label/);
    expect(() => fmt({ mean: 1, lo: 0.5, hi: 2 }, 'x', 'Verified-ish')).toThrow(/evidence label/);
  });
});
