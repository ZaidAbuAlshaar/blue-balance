import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, post } from '../api';
import { useStore, useT } from '../store';
import { Badge, Card, ErrorState, Loading } from '../ui';
import { explainError } from './WorkOrders';

const KIND: Record<string, string> = { tap_location: 'موقع توصيلة · tap location', new_connection: 'توصيلة جديدة · new connection', undocumented_segment: 'مقطع غير موثّق · undocumented segment' };
const STATUS: Record<string, string> = { draft: 'مسودة · draft', approved: 'معتمد · approved', rejected: 'مرفوض · rejected' };

export function MapEdits() {
  const t = useT();
  const user = useStore((s) => s.user);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['map-edits'], queryFn: () => api('/api/map-edits') });
  const [msg, setMsg] = useState<Record<string, string>>({});
  async function decide(id: string, approve: boolean) {
    try {
      const r = await post(`/api/map-edits/${id}/decide`, { approve, reason: approve ? 'verified on site (demo)' : 'not enough evidence (demo)' });
      setMsg((m) => ({ ...m, [id]: `${r.status} · ${r.decided_by}` }));
      qc.invalidateQueries({ queryKey: ['map-edits'] });
    } catch (e) { setMsg((m) => ({ ...m, [id]: explainError(e) })); }
  }
  async function exportEdit(id: string, crs: string) {
    try {
      const data = await api(`/api/map-edits/${id}/export?crs=${encodeURIComponent(crs)}`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/geo+json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `${id}_${crs.replace(':', '-')}.geojson`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      setMsg((m) => ({ ...m, [id]: `exported ${crs}` }));
    } catch (e) { setMsg((m) => ({ ...m, [id]: explainError(e) })); }
  }
  return (
    <div className="page">
      <div className="page-h">
        <h1>{t('تذكّر: تعديلات الخريطة', 'Remember: map edits')}</h1>
        <p className="lede">{t('كل نتيجة متحققة بتصير جزء من الخريطة — بعد موافقة مهندس ثاني. التصدير بنظام الإحداثيات الأردني أو WGS84.', 'Each verified result becomes part of the map — after a second engineer approves. Export in the Jordanian grid or WGS84.')}</p>
      </div>
      <Card title={t('التعديلات', 'Edits')} sub={t('اقترح تعديل من صفحة الحالة', 'Propose an edit from a case page')}>
        {q.isLoading && <Loading />}
        {q.error && <ErrorState error={q.error} what="map-edits" />}
        {q.data && q.data.map_edits.length === 0 && <p className="muted">{t('ما في تعديلات لسا. افتح حالة واضغط «اقترح تعديل خريطة».', 'No edits yet. Open a case and press "Propose map edit".')}</p>}
        <ul className="me-list">
          {q.data?.map_edits.map((e: any) => (
            <li key={e.edit_id} className={`me st-${e.status}`}>
              <div className="wo-h">
                <span className="mono" dir="ltr">{e.edit_id}</span>
                <a href={`#/case/${e.case_id}`} className="mono" dir="ltr">{e.case_id}</a>
                <span className="pill">{KIND[e.kind] ?? e.kind}</span>
                <span className="wo-status">{STATUS[e.status] ?? e.status}</span>
                <Badge label="Hypothesis" compact />
              </div>
              <div className="small mono muted" dir="ltr">{e.geometry?.type} {JSON.stringify(e.geometry?.coordinates?.map?.((c: number) => Math.round(c * 1e5) / 1e5))} · evidence {e.evidence_ids?.join(', ')}</div>
              <div className="small muted">{t('اقترح', 'Proposed by')} <span className="mono" dir="ltr">{e.proposed_by}</span>{e.decided_by && <> · {t('قرّر', 'decided by')} <span className="mono" dir="ltr">{e.decided_by}</span></>}</div>
              <div className="row-actions">
                {e.status === 'draft' && user?.role === 'engineer' && <>
                  <button className="btn primary sm" onClick={() => decide(e.edit_id, true)}>{t('اعتماد', 'Approve')}</button>
                  <button className="btn sm" onClick={() => decide(e.edit_id, false)}>{t('رفض', 'Reject')}</button>
                </>}
                {e.status === 'approved' && ['EPSG:28191', 'EPSG:4326', 'EPSG:3066'].map((crs) => (
                  <button key={crs} className="btn sm" onClick={() => exportEdit(e.edit_id, crs)}>{t('تصدير', 'Export')} <span className="mono" dir="ltr">{crs}</span></button>
                ))}
              </div>
              {msg[e.edit_id] && <div className={`small mono ${msg[e.edit_id].startsWith('HTTP') ? 'error' : 'ok'}`} dir="auto">{msg[e.edit_id]}</div>}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
