import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { useStore, useT } from '../store';
import { Badge, Card, ErrorState, Loading } from '../ui';
import { useMapCases } from './Overview';

export function Transparency() {
  const t = useT();
  const user = useStore((s) => s.user);
  const q = useQuery({ queryKey: ['transparency'], queryFn: () => api('/api/transparency') });
  const cases = useMapCases();
  const audit = useQuery({ queryKey: ['audit'], queryFn: () => api('/api/audit'), enabled: user?.role === 'admin' });
  const nField = cases.data?.features?.filter((f: any) => f.properties.layer === 'source').length;
  const caveats: [string, string, string?][] = [
    ['المسار تقريبي (من OpenStreetMap) — مش مخطط الشبكة الرسمي.', 'The route is approximate (from OpenStreetMap), not the official network plan.'],
    ['تقارير الطاقم اصطناعية، كتبناها للعرض. ما صارت زيارة ميدانية حقيقية.', 'Crew reports are synthetic, written for the demo. No real field visit took place.'],
    ['المرشّح مش مخالفة ولا سرقة — هو مكان يستاهل التفتيش.', 'A candidate is not a violation or theft — it is a place worth inspecting.'],
    ['Sentinel-2 بشوف استخدام المياه السطحي بس، ما بشوف الآبار ولا الأنابيب المدفونة.', 'Sentinel-2 sees surface water use only — not wells or buried pipes.'],
    [`كل مرشّحي الطبقة الأولى${typeof nField === 'number' ? ` (${nField})` : ''} داخل أرض زراعية قائمة — غالباً دورة زراعية.`, `All${typeof nField === 'number' ? ` ${nField}` : ''} Layer-1 candidates sit inside existing cropland (likely rotation).`, 'WorldCover'],
    ['إشارة الخط (عدم توازن التدفق) محاكاة — ما في عدّادات حقيقية متصلة.', 'The line signal (flow imbalance) is simulated — no real meters are connected.'],
    ['المستخرج بالنموذج والقواعد متقاربين باختبارنا: 90.9% مقابل 92.3% دقة حقول.', 'The LLM extractor and the rules are on par in our test: 90.9% vs 92.3% field accuracy.', 'eval/extract/RESULTS.md'],
  ];
  return (
    <div className="page">
      <div className="page-h">
        <h1>الشفافية <span className="muted">· Transparency</span></h1>
        <p className="lede">{t('شو بنعرف، شو بنفترض، وشو لسا ما تحققنا منه.', 'What we know, what we assume, and what is not verified yet.')}</p>
      </div>
      <div className="tr-grid">
        <Card title={t('الأدلة حسب الوسم', 'Evidence by label')}>
          {q.isLoading && <Loading />}
          {q.error && <ErrorState error={q.error} what="transparency" />}
          {q.data && (
            <ul className="counts">
              {['Observed', 'Simulated', 'Hypothesis', 'Field-verified'].map((l) => (
                <li key={l}><Badge label={l} /> <b className="num" dir="ltr">{q.data.evidence_by_label?.[l] ?? 0}</b></li>
              ))}
            </ul>
          )}
          {q.data && q.data.field_verified_count === 0 && <p className="muted small">{t('ما في ولا نتيجة متحققة ميدانياً لحد الآن.', 'No field-verified result exists yet.')}</p>}
        </Card>
        <Card title={t('تنبيهات ثابتة', 'Standing caveats')}>
          <ol className="caveats">
            {caveats.map(([ar, en, src]) => (
              <li key={en}><div dir="rtl">{ar}</div><div className="muted" dir="ltr">{en}{src && <span className="src"> · source: <span className="mono">{src}</span></span>}</div></li>
            ))}
          </ol>
        </Card>
      </div>
      <Card title={t('الافتراضات', 'Assumptions')} sub={t('كل افتراض إله رقم دليل', 'Every assumption has an evidence id')}>
        {q.data && (
          <table className="tbl">
            <thead><tr><th>{t('الوحدة', 'Module')}</th><th>{t('المفتاح', 'Key')}</th><th>{t('القيمة', 'Value')}</th><th>{t('المصدر', 'Source')}</th><th>{t('ملاحظة', 'Note')}</th><th>ID</th></tr></thead>
            <tbody>
              {q.data.assumptions.map((a: any) => (
                <tr key={a.evidence_id}>
                  <td className="mono" dir="ltr">{a.module}</td>
                  <td className="mono" dir="ltr">{a.key}</td>
                  <td className="mono" dir="ltr">{JSON.stringify(a.value)}</td>
                  <td><span className={`pill ${a.source === 'ASSUMED' ? 'prio-medium' : ''}`}>{a.source}</span></td>
                  <td dir="ltr" className="small">{a.note}</td>
                  <td className="mono small" dir="ltr">{a.evidence_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      {user?.role === 'admin' && (
        <Card title={t('سجل التدقيق', 'Audit log')} sub={t('سلسلة مترابطة بالتجزئة', 'Hash-chained')}>
          {audit.error && <ErrorState error={audit.error} what="audit" />}
          {audit.data && <p className="small mono" dir="ltr">chain: {JSON.stringify(audit.data.chain)} · rows: {audit.data.rows.length}</p>}
        </Card>
      )}
    </div>
  );
}
