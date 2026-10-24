import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { post } from '../api';
import { useT } from '../store';
import { isInterval, num } from '../fmt';
import { Badge, Card, ErrorState, LayerTag, Loading, Num, Point } from '../ui';

const SUGGESTED = [
  'شو أول ٣ مواقع لازم نفتشها بالكرك؟',
  'ليش KRK-T-002 بأول القائمة؟',
  'شو أفضل قياس تالي؟',
  'مين صاحب المزرعة KRK-F-001؟',
];

const MODE: Record<string, [string, string, string]> = {
  answer: ['جواب', 'answer', 'teal'],
  refusal: ['رفض', 'refusal', 'amber'],
  template: ['قالب', 'template', 'blue'],
  no_evidence: ['ما في دليل', 'no evidence', 'grey'],
};

const UNIT: Record<string, string> = { m3_per_insp_hour: 'm³/day/h', volume_m3_day: 'm³/day', p: '', probability: '', lr: '' };

/** Find every Interval inside a tool result, so the card can show the numbers the model left out. */
function intervals(obj: any, path: string[] = [], out: { key: string; iv: any }[] = []) {
  if (!obj || typeof obj !== 'object') return out;
  if (isInterval(obj)) { out.push({ key: path.join('.'), iv: obj }); return out; }
  for (const [k, v] of Object.entries(obj)) if (!['queue', 'measurements', 'layer_contributions'].includes(k)) intervals(v, [...path, k], out);
  return out;
}

function ToolCard({ call }: { call: any }) {
  const t = useT();
  const r = call.result ?? {};
  const label = r.label;
  return (
    <div className="toolcard">
      <div className="tc-h">
        <span className="mono tc-name" dir="ltr">{call.name}</span>
        <span className="mono muted small" dir="ltr">{JSON.stringify(call.args ?? {})}</span>
        {label && <Badge label={label} />}
      </div>
      {r.error ? <div className="error small">{t('الأداة رجّعت خطأ', 'Tool returned an error')}: <span className="mono" dir="ltr">{r.error}</span></div> : null}
      {Array.isArray(r.queue) && (
        <table className="tbl">
          <thead><tr><th>#</th><th>{t('الحالة', 'Case')}</th><th>m³/day/h</th><th>p</th></tr></thead>
          <tbody>{r.queue.map((q: any) => (
            <tr key={q.case_id}><td>{q.rank}</td><td><a href={`#/case/${q.case_id}`} className="mono" dir="ltr">{q.case_id}</a> <LayerTag layer={q.layer} /></td>
              <td><Num iv={q.m3_per_insp_hour} unit="" label={q.label} badge={false} /></td><td><Num iv={q.p} label={q.label} badge={false} /></td></tr>
          ))}</tbody>
        </table>
      )}
      {Array.isArray(r.measurements) && (
        <ul className="tc-list">{r.measurements.map((m: any) => (
          <li key={m.measurement_id}><span className="mono" dir="ltr">{m.kind} → {m.target_id}</span> · {t('معلومة', 'info')} <Point v={m.expected_info_gain_bits} unit="bits" /> · <bdi dir="ltr" className="num">{m.cost_h} h</bdi></li>
        ))}</ul>
      )}
      {Array.isArray(r.layer_contributions) && (
        <ul className="tc-list">{r.layer_contributions.map((s: any) => (
          <li key={s.evidence_id}><LayerTag layer={s.layer} /> LR <Num iv={s.lr} label={s.label} /> <span className="muted small" dir="auto">{s.signal}</span></li>
        ))}</ul>
      )}
      {intervals(r).length > 0 && (
        <div className="tc-ivs">{intervals(r).map((x) => (
          <div key={x.key} className="tc-iv"><span className="mono muted small" dir="ltr">{x.key}</span> <Num iv={x.iv} unit={UNIT[x.key.split('.').pop() ?? ''] ?? ''} label={label} /></div>
        ))}</div>
      )}
      {(r.rank_before !== undefined) && <div className="small">rank <bdi dir="ltr">#{r.rank_before} → #{r.rank_after}</bdi></div>}
      {r.wo_id && <div className="small mono" dir="ltr">{r.wo_id} · {r.status}</div>}
    </div>
  );
}

export function Ask() {
  const t = useT();
  const [q, setQ] = useState('');
  const m = useMutation({ mutationFn: (question: string) => post('/api/agent/ask', { question }) });
  const d = m.data;
  const ask = (text: string) => { setQ(text); m.mutate(text); };
  const mode = d ? MODE[d.mode] ?? [d.mode, d.mode, 'grey'] : null;
  return (
    <div className="page">
      <div className="page-h">
        <h1>{t('اسأل المساعد', 'Ask the agent')}</h1>
        <p className="lede">{t('نموذج محلي مع أدوات. الأرقام بتيجي من الأدوات، والبطاقات تحت الجواب بتعرض الفواصل اللي النموذج ممكن يحذفها.', 'A local model with tools. Numbers come from tools; the cards under the answer show the intervals the model may omit.')}</p>
      </div>
      <div className="ask-grid">
        <Card title={t('السؤال', 'Question')}>
          <form className="askform" onSubmit={(e) => { e.preventDefault(); if (q.trim()) m.mutate(q.trim()); }}>
            <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} dir="auto" placeholder={t('اكتب سؤالك بالعربي…', 'Type your question…')} maxLength={1000} aria-label="question" />
            <button className="btn primary" type="submit" disabled={m.isPending || !q.trim()}>{t('اسأل', 'Ask')}</button>
          </form>
          <div className="suggest">
            <div className="muted small">{t('أسئلة مقترحة', 'Suggested questions')}</div>
            {SUGGESTED.map((s) => <button key={s} className="btn ghost sug" onClick={() => ask(s)} disabled={m.isPending}>{s}</button>)}
          </div>
        </Card>
        <div>
          {m.isPending && <Card title={t('الجواب', 'Answer')}><Loading text={t('النموذج المحلي بفكّر… (ممكن ياخذ ثواني)', 'Local model thinking… (may take seconds)')} /></Card>}
          {m.error && <ErrorState error={m.error} what="agent" />}
          {d && mode && (
            <Card title={t('الجواب', 'Answer')} right={<span className={`mode tone-${mode[2]}`}>{mode[0]} · {mode[1]}</span>}>
              <div className="answer">{String(d.answer ?? '').split(/\n\s*\n/).map((para: string, i: number) => <p key={i} dir="auto">{para}</p>)}</div>
              <div className="meta small muted">
                <span>{t('النموذج', 'Model')}: <span className="mono" dir="ltr">{d.model ?? '—'}</span></span>
                <span>{t('الزمن', 'Latency')}: <bdi className="num" dir="ltr">{typeof d.timing?.total_s === 'number' ? (d.timing.total_s < 1 ? `${Math.round(d.timing.total_s * 1000)} ms` : `${num(d.timing.total_s, 1)} s`) : '—'}</bdi></span>
                {d.evidence_ids?.length > 0 && <span>{t('الأدلة', 'Evidence')}: <span className="mono" dir="ltr">{d.evidence_ids.join(', ')}</span></span>}
                {d.checks?.flags?.length > 0 && <span className="warn-inline">{t('تنبيه', 'Flags')}: <span className="mono" dir="ltr">{d.checks.flags.join(', ')}</span></span>}
              </div>
              <h3 className="h3">{t('نتائج الأدوات', 'Tool results')} <span className="muted small">· {d.tool_calls?.length ?? 0}</span></h3>
              {(d.tool_calls ?? []).length === 0 && <p className="muted small">{t('ما انستدعت أي أداة.', 'No tool was called.')}</p>}
              {(d.tool_calls ?? []).map((c: any, i: number) => <ToolCard key={i} call={c} />)}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
