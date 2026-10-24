import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, post } from '../api';
import { useStore, useT } from '../store';
import { Badge, Card, ErrorState, Loading } from '../ui';
import { useQueue } from './Overview';

const TASKS: Record<string, [string, string]> = {
  inspect_connection: ['فحص توصيلة', 'Inspect connection'],
  inspect_leak: ['فحص تسريب', 'Inspect leak'],
  inspect_field: ['فحص حقل', 'Inspect field'],
};
const PRIO: Record<string, [string, string]> = { high: ['عالية', 'high'], medium: ['متوسطة', 'medium'], low: ['منخفضة', 'low'] };
const STATUS: Record<string, string> = { pending_approval: 'بانتظار الموافقة · pending approval', approved: 'موافق عليه · approved', rejected: 'مرفوض · rejected' };

export function explainError(e: unknown): string {
  const err = e as ApiError;
  const b = err?.body as any;
  const raw = `HTTP ${err?.status ?? '?'} · ${JSON.stringify(b ?? err?.message)}`;
  if (err?.status === 403) return `${raw} — الموافقة لازم تكون من مهندس غير صاحب الطلب · Approval must come from a different engineer than the requester`;
  return raw;
}

function CreateForm({ prefill }: { prefill: string | null }) {
  const t = useT();
  const qc = useQueryClient();
  const queue = useQueue(25);
  const [caseId, setCaseId] = useState(prefill ?? 'KRK-T-002');
  const [task, setTask] = useState(prefill?.includes('-F-') ? 'inspect_field' : 'inspect_connection');
  const [prio, setPrio] = useState('high');
  const [ar, setAr] = useState('');
  const [en, setEn] = useState('');
  const [crew, setCrew] = useState('');
  const fill = () => {
    setAr(`${TASKS[task][0]} عند ${caseId} — مرشّح للتفتيش، مش مخالفة.`);
    setEn(`${TASKS[task][1]} at ${caseId} — inspection candidate, not a violation.`);
    setCrew(`روحوا على ${caseId}، صوّروا وارجعوا بنتيجة.`);
  };
  const m = useMutation({
    mutationFn: () => post('/api/work-orders', { case_id: caseId, task, priority: prio, text_ar: ar, text_en: en, crew_ar: crew }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders'] }),
  });
  return (
    <Card title={t('مسودة أمر عمل', 'Draft work order')} sub={t('مهندس يطلب، ومهندس ثاني يوافق', 'One engineer requests, a different engineer approves')} right={<Badge label="Simulated" />}>
      <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
        <label className="field"><span>{t('الحالة', 'Case')}</span>
          <select value={caseId} onChange={(e) => setCaseId(e.target.value)} dir="ltr">
            {(queue.data?.queue ?? [{ case_id: caseId }]).map((q: any) => <option key={q.case_id} value={q.case_id}>{q.rank ? `#${q.rank} ` : ''}{q.case_id}</option>)}
          </select>
        </label>
        <div className="row2">
          <label className="field"><span>{t('المهمة', 'Task')}</span>
            <select value={task} onChange={(e) => setTask(e.target.value)}>{Object.entries(TASKS).map(([k, v]) => <option key={k} value={k}>{v[0]} · {v[1]}</option>)}</select>
          </label>
          <label className="field"><span>{t('الأولوية', 'Priority')}</span>
            <select value={prio} onChange={(e) => setPrio(e.target.value)}>{Object.entries(PRIO).map(([k, v]) => <option key={k} value={k}>{v[0]} · {v[1]}</option>)}</select>
          </label>
        </div>
        <label className="field"><span>{t('النص بالعربي', 'Arabic text')}</span><textarea value={ar} onChange={(e) => setAr(e.target.value)} rows={2} dir="rtl" /></label>
        <label className="field"><span>{t('النص بالإنجليزي', 'English text')}</span><textarea value={en} onChange={(e) => setEn(e.target.value)} rows={2} dir="ltr" /></label>
        <label className="field"><span>{t('تعليمات الطاقم', 'Crew instructions (Arabic)')}</span><textarea value={crew} onChange={(e) => setCrew(e.target.value)} rows={2} dir="rtl" /></label>
        <div className="row-actions">
          <button type="button" className="btn ghost" onClick={fill}>{t('عبّي نص مقترح', 'Fill suggested text')}</button>
          <button type="submit" className="btn primary" disabled={m.isPending || !ar || !en || !crew}>{t('أنشئ المسودة', 'Create draft')}</button>
        </div>
        {m.error && <div className="error mono small" dir="auto">{explainError(m.error)}</div>}
        {m.data && <div className="ok small"><span className="mono" dir="ltr">{m.data.wo_id}</span> · {STATUS[m.data.status] ?? m.data.status} · {t('بدها موافقة مهندس ثاني', 'needs a different engineer to approve')}</div>}
      </form>
    </Card>
  );
}

export function WorkOrders({ prefillCase }: { prefillCase: string | null }) {
  const t = useT();
  const user = useStore((s) => s.user);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['work-orders'], queryFn: () => api('/api/work-orders') });
  const [msg, setMsg] = useState<Record<string, string>>({});
  async function decide(id: string, approve: boolean) {
    try {
      const r = await post(`/api/work-orders/${id}/${approve ? 'approve' : 'reject'}`);
      setMsg((m) => ({ ...m, [id]: `${r.status} · ${r.decided_by}` }));
      qc.invalidateQueries({ queryKey: ['work-orders'] });
    } catch (e) { setMsg((m) => ({ ...m, [id]: explainError(e) })); }
  }
  return (
    <div className="page">
      <div className="page-h">
        <h1>{t('أوامر العمل', 'Work orders')}</h1>
        <p className="lede">{t('الموافقة بشرية دايماً ومن مهندس غير اللي طلب — الخادم بيفرض هالشي.', 'Approval is always human and by a different engineer than the requester — enforced by the server.')}</p>
      </div>
      <div className="wo-grid">
        {user?.role === 'engineer' ? <CreateForm prefill={prefillCase} /> : <Card title={t('مسودة أمر عمل', 'Draft work order')}><p className="muted">{t('بس المهندس بقدر ينشئ مسودة.', 'Only engineers can draft work orders.')}</p></Card>}
        <Card title={t('القائمة', 'List')} sub={<>{t('مسجّل دخول', 'Signed in as')} <span className="mono" dir="ltr">{user?.user_id}</span></>}>
          {q.isLoading && <Loading />}
          {q.error && <ErrorState error={q.error} what="work-orders" />}
          {q.data && q.data.work_orders.length === 0 && <p className="muted">{t('ما في أوامر عمل لسا.', 'No work orders yet.')}</p>}
          <ul className="wo-list">
            {q.data?.work_orders.map((w: any) => (
              <li key={w.wo_id} className={`wo st-${w.status}`}>
                <div className="wo-h">
                  <span className="mono" dir="ltr">{w.wo_id}</span>
                  <a href={`#/case/${w.case_id}`} className="mono" dir="ltr">{w.case_id}</a>
                  <span className="pill">{TASKS[w.task]?.[0] ?? w.task}</span>
                  <span className={`pill prio-${w.priority}`}>{PRIO[w.priority]?.[0] ?? w.priority}</span>
                  <span className="wo-status">{STATUS[w.status] ?? w.status}</span>
                </div>
                <div className="wo-t" dir="rtl">{w.text_ar}</div>
                <div className="wo-t muted" dir="ltr">{w.text_en}</div>
                <div className="small muted">{t('طلب', 'Requested by')} <span className="mono" dir="ltr">{w.requested_by}</span> ({w.requested_via}){w.decided_by && <> · {t('قرّر', 'decided by')} <span className="mono" dir="ltr">{w.decided_by}</span></>}</div>
                {w.status === 'pending_approval' && user?.role === 'engineer' && (
                  <div className="row-actions">
                    <button className="btn primary sm" onClick={() => decide(w.wo_id, true)}>{t('موافقة', 'Approve')}</button>
                    <button className="btn sm" onClick={() => decide(w.wo_id, false)}>{t('رفض', 'Reject')}</button>
                  </div>
                )}
                {msg[w.wo_id] && <div className={`small mono ${msg[w.wo_id].startsWith('HTTP') ? 'error' : 'ok'}`} dir="auto">{msg[w.wo_id]}</div>}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
