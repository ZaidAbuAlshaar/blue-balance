import { useEffect, useState, type ReactNode } from 'react';
import { ApiError } from './api';
import { fmt, isInterval, isLabel, num, type EvidenceLabel, type Interval } from './fmt';

const LABEL_TEXT: Record<EvidenceLabel, [string, string]> = {
  Observed: ['مرصود', 'Observed'],
  Simulated: ['محاكاة', 'Simulated'],
  Hypothesis: ['فرضية', 'Hypothesis'],
  'Field-verified': ['متحقَّق ميدانياً', 'Field-verified'],
};

function BadgeIcon({ label }: { label: EvidenceLabel }) {
  if (label === 'Observed') return <svg width="11" height="11" aria-hidden><rect x="0.5" y="0.5" width="10" height="10" fill="currentColor" /></svg>;
  if (label === 'Simulated') return <svg width="11" height="11" aria-hidden><rect x="1" y="1" width="9" height="9" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2.2 1.6" /></svg>;
  if (label === 'Hypothesis')
    return (
      <svg width="11" height="11" aria-hidden>
        <defs><pattern id="bb-hatch" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="3" stroke="currentColor" strokeWidth="1.4" /></pattern></defs>
        <rect x="0.5" y="0.5" width="10" height="10" fill="url(#bb-hatch)" stroke="currentColor" strokeWidth="1" />
      </svg>
    );
  return <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden><path d="M1.5 6.5l3 3 6-7" fill="none" stroke="currentColor" strokeWidth="2" /></svg>;
}

/** The one evidence badge used everywhere: icon + text, never colour alone. */
export function Badge({ label, compact = false }: { label: string | undefined | null; compact?: boolean }) {
  if (!isLabel(label)) return <span className="badge badge-unknown">؟ بلا وسم · unlabelled</span>;
  const [ar, en] = LABEL_TEXT[label];
  return (
    <span className={`badge badge-${label.toLowerCase()}`} title={`${ar} · ${en}`}>
      <BadgeIcon label={label} />
      <span>{compact ? en : `${ar} · ${en}`}</span>
    </span>
  );
}

/** Value with interval + evidence label, or an honest refusal to show it. */
export function Num({ iv, unit = '', label, digits, badge = true }: { iv: Interval | null | undefined; unit?: string; label: string | undefined | null; digits?: number; badge?: boolean }) {
  let text: string;
  try { text = fmt(iv, unit, label, digits); } catch {
    return <span className="num-missing">قيمة محجوبة: بلا فاصل أو وسم · withheld (no interval/label)</span>;
  }
  return (
    <span className="numwrap">
      <bdi className="num" dir="ltr">{text}</bdi>
      {badge && <Badge label={label} compact />}
    </span>
  );
}

/** A backend value that has no interval: shown, but flagged as a point estimate. */
export function Point({ v, unit = '', digits = 2, label }: { v: number | null | undefined; unit?: string; digits?: number; label?: string }) {
  if (typeof v !== 'number') return <span className="num-missing">—</span>;
  return (
    <span className="numwrap">
      <bdi className="num" dir="ltr">{num(v, digits)}{unit ? ` ${unit}` : ''}</bdi>
      <span className="point-tag">تقدير نقطي · point, no interval</span>
      {label && <Badge label={label} compact />}
    </span>
  );
}

export function ErrorState({ error, what }: { error: unknown; what?: string }) {
  const e = error as ApiError;
  const status = e?.status;
  let hint = '';
  if (status === 404) hint = 'الخدمة غير متاحة بعد · endpoint not available yet';
  else if (status === 403) hint = 'غير مسموح لهذا الدور · not permitted for this role';
  else if (status === 401) hint = 'لازم تسجيل دخول · login required';
  return (
    <div className="error" role="alert">
      <strong>تعذّر التحميل · Could not load{what ? ` — ${what}` : ''}</strong>
      <div className="mono" dir="ltr">{status ? `HTTP ${status} · ` : ''}{e?.message ?? String(error)}</div>
      {hint && <div>{hint}</div>}
    </div>
  );
}

export function Loading({ text }: { text?: string }) {
  return <div className="loading">{text ?? 'جارِ التحميل… · Loading…'}</div>;
}

export function Card({ title, sub, children, right, className = '' }: { title: ReactNode; sub?: ReactNode; children: ReactNode; right?: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      <header className="card-h">
        <div>
          <h2>{title}</h2>
          {sub && <div className="sub">{sub}</div>}
        </div>
        {right}
      </header>
      <div className="card-b">{children}</div>
    </section>
  );
}

export function LayerTag({ layer }: { layer: string }) {
  return layer === 'transmission'
    ? <span className="layer layer-t">خط رئيسي · Main line</span>
    : <span className="layer layer-s">حقل · Field</span>;
}

/** Interval bar on [0,1]: band lo–hi, dot at mean, optional prior tick. */
export function ProbBar({ iv, prior, tone = 'blue', animateFrom }: { iv: Interval | null; prior?: number; tone?: 'blue' | 'teal' | 'amber' | 'grey'; animateFrom?: Interval | null }) {
  const [shown, setShown] = useState<Interval | null>(animateFrom ?? iv);
  useEffect(() => {
    if (!animateFrom) { setShown(iv); return; }
    setShown(animateFrom);
    const t = setTimeout(() => setShown(iv), 60);
    return () => clearTimeout(t);
  }, [iv?.mean, iv?.lo, iv?.hi, animateFrom?.mean]);
  if (!isInterval(shown)) return <div className="probbar empty" />;
  const pct = (x: number) => `${Math.max(0, Math.min(1, x)) * 100}%`;
  return (
    <div className={`probbar tone-${tone}`} dir="ltr">
      <div className="pb-band" style={{ left: pct(shown.lo), width: `calc(${pct(shown.hi)} - ${pct(shown.lo)})` }} />
      <div className="pb-mean" style={{ left: pct(shown.mean) }} />
      {typeof prior === 'number' && <div className="pb-prior" style={{ left: pct(prior) }} title="prior" />}
      <div className="pb-ticks"><span>0</span><span>0.5</span><span>1</span></div>
    </div>
  );
}
