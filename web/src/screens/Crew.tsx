import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api, post } from '../api';
import { useT } from '../store';
import { Badge, ErrorState, Loading } from '../ui';

const FIELDS: [string, string, string][] = [
  ['site_id', 'رمز الموقع', 'Site ID'],
  ['location', 'الموقع', 'Location'],
  ['nearest_asset', 'أقرب منشأة', 'Nearest asset'],
  ['observation_type', 'نوع الملاحظة', 'Observation'],
  ['water_use', 'استخدام المياه', 'Water use'],
  ['flow_or_size', 'التدفق أو الحجم', 'Flow or size'],
  ['evidence_attached', 'دليل مرفق', 'Evidence attached'],
  ['severity', 'الخطورة', 'Severity'],
  ['datetime', 'الوقت', 'Date/time'],
  ['notes_action', 'ملاحظات وإجراء', 'Notes/action'],
];

const FLAG: Record<string, string> = {
  possible_injection: 'تعليمات مدسوسة محتملة بالتقرير · possible injected instruction',
  conflicting_cues: 'إشارات متعارضة · conflicting cues',
  span_in_instruction: 'القيمة مأخوذة من جملة تعليمات · value sits inside an instruction',
};

function flagText(f: string) {
  const [k, field] = f.split(':');
  return `${FLAG[k] ?? k}${field ? ` — ${field}` : ''}`;
}

/** Report text with the source words of each field highlighted. Indices are code points (Python). */
function Highlighted({ text, fields, active }: { text: string; fields: Record<string, any>; active: string | null }) {
  const chars = Array.from(text);
  const spans: { s: number; e: number; key: string; cand?: boolean }[] = [];
  Object.entries(fields).forEach(([k, f]) => {
    if (typeof f?.start === 'number' && typeof f?.end === 'number') spans.push({ s: f.start, e: f.end, key: k });
    (f?.candidates ?? []).forEach((c: any) => typeof c.start === 'number' && spans.push({ s: c.start, e: c.end, key: k, cand: true }));
  });
  spans.sort((a, b) => a.s - b.s);
  const out: React.ReactNode[] = [];
  let i = 0;
  spans.forEach((sp, n) => {
    if (sp.s < i) return; // skip overlaps
    if (sp.s > i) out.push(chars.slice(i, sp.s).join(''));
    out.push(<mark key={n} className={`${sp.cand ? 'cand' : ''} ${active === sp.key ? 'on' : ''}`} title={sp.key}>{chars.slice(sp.s, sp.e).join('')}</mark>);
    i = sp.e;
  });
  if (i < chars.length) out.push(chars.slice(i).join(''));
  return <div className="hl-text" dir="rtl">{out}</div>;
}

export function Crew() {
  const t = useT();
  const demo = useQuery({ queryKey: ['demo-reports'], queryFn: () => api('/api/demo/reports') });
  const [rid, setRid] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [useLlm, setUseLlm] = useState(false);
  const [fields, setFields] = useState<Record<string, any> | null>(null);
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    const reports = demo.data?.reports;
    if (reports?.length && rid === null) { setRid(reports[0].id); setText(reports[0].text); }
  }, [demo.data]);
  const ex = useMutation({ mutationFn: () => post('/api/reports/extract', { text, use_llm: useLlm }), onSuccess: (d) => setFields(structuredClone(d.fields)) });
  const sub = useMutation({
    mutationFn: () => {
      const site = fields?.site_id?.value;
      return post('/api/reports', { case_id: typeof site === 'string' ? site : null, text, fields, method: ex.data?.method, flags: ex.data?.flags ?? [] });
    },
  });
  const pending = useMemo(() => Object.values(fields ?? {}).filter((f: any) => f?.status === 'needs_confirmation').length, [fields]);
  function choose(key: string, c: any) {
    setFields((fs) => ({ ...fs, [key]: { ...fs![key], value: c.value, span: c.span, start: c.start, end: c.end, status: 'confirmed', confirmed_from: 'candidates' } }));
  }
  const report = demo.data?.reports?.find((r: any) => r.id === rid);
  return (
    <div className="page crew-page">
      <div className="page-h">
        <h1>{t('تحقّق: تقرير الطاقم', 'Verify: crew report')}</h1>
        <p className="lede">{t('الطاقم يكتب بلهجته، والمستخرج يعبّي ١٠ حقول — وكل قيمة بتأشّر على كلماتها بالتقرير. اللي ما إله دليل بضل فاضي.', 'The crew writes in dialect; the extractor fills 10 fields, each pointing at its source words. No evidence, no value.')}</p>
      </div>
      <div className="phone">
        <div className="phone-notch" />
        <div className="phone-screen">
          <div className="ph-h">
            <b>{t('تقرير ميداني', 'Field report')}</b>
            <Badge label={demo.data?.label ?? 'Simulated'} compact />
          </div>
          {demo.isLoading && <Loading />}
          {demo.error && <ErrorState error={demo.error} what="demo/reports" />}
          {demo.data && (
            <>
              <div className="synthetic-note">{t('تقارير اصطناعية للعرض — ما صارت زيارة حقيقية', 'Synthetic reports for the demo — no real visit')}</div>
              <select className="ph-select" value={rid ?? ''} onChange={(e) => { const r = demo.data.reports.find((x: any) => x.id === e.target.value); setRid(r.id); setText(r.text); setFields(null); ex.reset(); sub.reset(); }} aria-label="demo report">
                {demo.data.reports.map((r: any) => <option key={r.id} value={r.id}>{r.id} · {r.title_ar ?? ''} · {r.title_en ?? ''}</option>)}
              </select>
            </>
          )}
          <textarea className="ph-text" value={text} onChange={(e) => { setText(e.target.value); setFields(null); }} rows={5} dir="rtl" maxLength={2000} aria-label="report text" />
          <div className="ph-row">
            <label className="toggle">
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
              <span>{useLlm ? t('النموذج (Gemma)', 'LLM (Gemma)') : t('القواعد', 'Rules')}</span>
            </label>
            <button className="btn primary" onClick={() => ex.mutate()} disabled={!text.trim() || ex.isPending} data-action="extract">{ex.isPending ? '…' : t('استخرج', 'Extract')}</button>
          </div>
          {ex.error && <ErrorState error={ex.error} what="extract" />}
          {ex.data && fields && (
            <>
              <div className="ph-meta small muted">
                {t('الطريقة', 'Method')}: <span className="mono" dir="ltr">{ex.data.method}{ex.data.model ? ` · ${ex.data.model}` : ''}</span>
              </div>
              {ex.data.flags?.length > 0 && (
                <div className="flags" role="alert">
                  <b>{t('تحذير', 'Warning')}</b>
                  <ul>{ex.data.flags.map((f: string) => <li key={f}>{flagText(f)}</li>)}</ul>
                </div>
              )}
              <Highlighted text={text} fields={fields} active={active} />
              <ul className="xfields">
                {FIELDS.map(([k, ar, en]) => {
                  const f = fields[k] ?? { status: 'empty_no_evidence' };
                  return (
                    <li key={k} className={`xf st-${f.status}`} onMouseEnter={() => setActive(k)} onMouseLeave={() => setActive(null)}>
                      <div className="xf-l">{ar} <span>· {en}</span></div>
                      {f.status === 'needs_confirmation' ? (
                        <div className="xf-confirm">
                          <div className="small amber">{t('لازم تأكيد — اختار وحدة', 'Needs confirmation — pick one')}</div>
                          <div className="xf-cands">
                            {(f.candidates ?? []).map((c: any) => (
                              <button key={`${c.value}-${c.start}`} className="btn sm" onClick={() => choose(k, c)}>
                                <b className="mono" dir="ltr">{c.value}</b> «{c.span}»
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : f.value === null || f.value === undefined ? (
                        <div className="xf-empty">ما في دليل · no evidence</div>
                      ) : (
                        <div className="xf-v">
                          <span className="mono" dir="ltr">{String(f.value)}</span>
                          {f.span && <span className="xf-span">«{f.span}»</span>}
                          {f.status === 'confirmed' && <span className="small teal">{t('مؤكَّد', 'confirmed')}</span>}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
              <button className="btn primary wide" disabled={pending > 0 || sub.isPending || sub.isSuccess} onClick={() => sub.mutate()} data-action="submit">
                {pending > 0 ? t(`أكّد ${pending} حقل أول`, `Confirm ${pending} field(s) first`) : t('تأكيد وإرسال', 'Confirm & submit')}
              </button>
              {sub.error && <ErrorState error={sub.error} what="reports" />}
              {sub.data && <div className="ok small">{t('انحفظ', 'Saved')} <span className="mono" dir="ltr">{sub.data.report_id}</span> · <Badge label={sub.data.label} compact /> · {sub.data.confirmed_by}</div>}
            </>
          )}
          {report && !fields && <p className="muted small">{t('اضغط «استخرج» لتعبئة الحقول.', 'Press Extract to fill the fields.')}</p>}
        </div>
      </div>
    </div>
  );
}
