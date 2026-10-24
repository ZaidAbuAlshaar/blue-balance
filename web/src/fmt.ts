// Number formatting with honesty rules: a value is only rendered together with its interval and an evidence label.
export const LABELS = ['Observed', 'Simulated', 'Hypothesis', 'Field-verified'] as const;
export type EvidenceLabel = (typeof LABELS)[number];
export interface Interval { mean: number; lo: number; hi: number }

const cache = new Map<number, Intl.NumberFormat>();
function nf(digits: number): Intl.NumberFormat {
  let f = cache.get(digits);
  if (!f) {
    // Western (latn) digits always, Jordanian Arabic locale conventions otherwise.
    f = new Intl.NumberFormat('ar-JO-u-nu-latn', { minimumFractionDigits: digits, maximumFractionDigits: digits });
    cache.set(digits, f);
  }
  return f;
}

export function num(x: number, digits = 1): string {
  if (typeof x !== 'number' || !Number.isFinite(x)) throw new Error('num: not a finite number');
  return nf(digits).format(x);
}

export function isInterval(v: unknown): v is Interval {
  if (!v || typeof v !== 'object') return false;
  const o = v as Record<string, unknown>;
  return ['mean', 'lo', 'hi'].every((k) => typeof o[k] === 'number' && Number.isFinite(o[k] as number));
}

export function isLabel(v: unknown): v is EvidenceLabel {
  return typeof v === 'string' && (LABELS as readonly string[]).includes(v);
}

/** "244.1 (100.6–408.6) m³/day/h". Throws if the interval (mean, lo, hi) or the evidence label is missing. */
export function fmt(iv: Interval | null | undefined, unit: string, label: EvidenceLabel | string | null | undefined, digits?: number): string {
  if (!isInterval(iv)) throw new Error('fmt: refusing to render a value without mean, lo and hi');
  if (!isLabel(label)) throw new Error('fmt: refusing to render a value without an evidence label');
  const d = digits ?? (Math.abs(iv.hi) <= 1 && Math.abs(iv.lo) <= 1 ? 2 : 1);
  const s = `${num(iv.mean, d)} (${num(iv.lo, d)}–${num(iv.hi, d)})`;
  return unit ? `${s} ${unit}` : s;
}
