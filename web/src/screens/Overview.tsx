import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { useStore, useT } from '../store';
import { go } from '../route';
import { MapView } from '../MapView';
import { Badge, Card, ErrorState, LayerTag, Loading, Num, Point } from '../ui';

export const useQueue = (limit = 10) => useQuery({ queryKey: ['queue', limit], queryFn: () => api(`/api/queue?limit=${limit}`) });
export const useMapCases = () => useQuery({ queryKey: ['map-cases'], queryFn: () => api('/api/map/cases') });
export const useRouteGeo = () => useQuery({ queryKey: ['map-route'], queryFn: () => api('/api/map/route'), staleTime: Infinity });

const KIND: Record<string, string> = {
  flow_meter_read: 'قراءة عدّادات التدفق · flow-meter read',
  field_visit: 'زيارة ميدانية · field visit',
};

function ImpactStrip() {
  const t = useT();
  const q = useQuery({ queryKey: ['impact'], queryFn: () => api('/api/impact') });
  if (q.isLoading) return <div className="impact"><Loading /></div>;
  if (q.error) return <div className="impact"><ErrorState error={q.error} what={t('الأثر المتوقع', 'expected impact')} /></div>;
  const d = q.data;
  const tiles = [
    { ar: 'فاقد متوقع يمكن إيقافه', en: 'Expected loss stoppable', iv: d.expected_m3_day, unit: 'm³/day' },
    { ar: 'طاقة ضخ', en: 'Pumping energy', iv: d.kwh_day, unit: 'kWh/day' },
    { ar: 'انبعاثات مكافئة', en: 'Equivalent CO₂', iv: d.co2_kg_day, unit: 'kg CO₂/day' },
  ];
  return (
    <div className="impact">
      <div className="impact-h">
        <div>
          <b>{t('الأثر المتوقع', 'Expected impact')}</b>
          <span className="muted"> · {t(`أعلى ${d.top_n} حالات`, `top ${d.top_n} cases`)}</span>
        </div>
        <Badge label={d.label} />
      </div>
      <div className="impact-tiles">
        {tiles.map((x) => (
          <div className="tile" key={x.en}>
            <div className="tile-l">{x.ar} <span>· {x.en}</span></div>
            <div className="tile-v"><Num iv={x.iv} unit={x.unit} label={d.label} badge={false} /></div>
          </div>
        ))}
      </div>
      <div className="impact-note">{t('خسارة متوقعة عند المرشحين، مش استرداد متحقق. ما في نتيجة ميدانية متحققة.', d.note ?? 'Expected loss, not verified recoveries.')}</div>
    </div>
  );
}

export function QueuePanel({ limit = 10 }: { limit?: number }) {
  const t = useT();
  const { selected, select } = useStore();
  const q = useQueue(limit);
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} what={t('قائمة الأولوية', 'priority queue')} />;
  const d = q.data;
  return (
    <div className="queue">
      <div className="queue-unit muted small">{t('م³ فاقد/يوم يتوقف لكل ساعة تفتيش', 'm³/day of loss stopped per inspection hour')} <Badge label={d.label} compact /></div>
      <ol className="qlist">
        {d.queue.map((c: any) => (
          <li key={c.case_id} className={`qitem ${selected === c.case_id ? 'sel' : ''}`} onClick={() => select(c.case_id)} data-case={c.case_id}>
            <div className="q-rank" aria-label="rank">{c.rank}</div>
            <div className="q-body">
              <div className="q-top">
                <bdi className="q-id mono" dir="ltr">{c.case_id}</bdi>
                <LayerTag layer={c.layer} />
                <span className="q-cand">{t('مرشّح', 'candidate')}</span>
              </div>
              <div className="q-main"><Num iv={c.m3_per_insp_hour} unit="m³/day/h" label={c.label} /></div>
              <div className="q-sub">
                <span>p <Num iv={c.p} label={c.label} badge={false} /></span>
                <span>{t('حجم', 'vol')} <Num iv={c.volume_m3_day} unit="m³/day" label={c.label} badge={false} /></span>
              </div>
            </div>
            <button className="btn sm" onClick={(e) => { e.stopPropagation(); go(`#/case/${encodeURIComponent(c.case_id)}`); }}>{t('فتح', 'Open')}</button>
          </li>
        ))}
      </ol>
    </div>
  );
}

function NextBest() {
  const t = useT();
  const q = useQuery({ queryKey: ['next-best'], queryFn: () => api('/api/next-best') });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} what={t('أفضل قياس تالي', 'next-best measurement')} />;
  return (
    <ol className="nb">
      {q.data.measurements.map((m: any, i: number) => (
        <li key={m.measurement_id} className={i === 0 ? 'nb-top' : ''}>
          <div className="nb-h">
            <span className="nb-kind">{KIND[m.kind] ?? m.kind}</span>
            <a className="mono" dir="ltr" href={`#/case/${encodeURIComponent(m.target_id)}`}>{m.target_id}</a>
            <Badge label={m.label} compact />
          </div>
          <div className="nb-nums">
            <span>{t('معلومة متوقعة', 'expected info')} <Point v={m.expected_info_gain_bits} unit="bits" /></span>
            <span>{t('كلفة', 'cost')} <bdi dir="ltr" className="num">{m.cost_h} h</bdi></span>
            <span>{t('لكل ساعة', 'per hour')} <bdi dir="ltr" className="num">{m.gain_per_hour} bits/h</bdi></span>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Overview() {
  const t = useT();
  const { selected, select } = useStore();
  const cases = useMapCases();
  const route = useRouteGeo();
  return (
    <div className="page">
      <div className="page-h">
        <h1>{t('اكتشف · وين نروح أول؟', 'Detect · where do we go first?')}</h1>
        <p className="lede">{t('ترتيب المواقع حسب م³ الفاقد المتوقع إيقافه لكل ساعة تفتيش، مع فاصل الثقة ووسم الدليل لكل رقم.', 'Sites ranked by expected m³ of loss stopped per inspection hour, every number with its interval and evidence label.')}</p>
      </div>
      <ImpactStrip />
      <div className="ov-grid">
        <Card title={t('خريطة الكرك', 'Karak map')} sub={t('اضغط على مقطع أو حقل لاختيار الحالة', 'Click a segment or field to select its case')} className="ov-map"
          right={selected ? <button className="btn primary sm" onClick={() => go(`#/case/${encodeURIComponent(selected)}`)}>{t('افتح', 'Open')} <bdi dir="ltr">{selected}</bdi></button> : undefined}>
          {cases.error ? <ErrorState error={cases.error} what="map/cases" /> : null}
          {route.error ? <ErrorState error={route.error} what="map/route" /> : null}
          <MapView cases={cases.data} route={route.data} selected={selected} onSelect={select} height={520} />
        </Card>
        <div className="ov-side">
          <Card title={t('قائمة الأولوية', 'Priority queue')} sub={t('مرشّحون للتفتيش — مش مخالفات', 'Candidates for inspection — not violations')}>
            <QueuePanel />
          </Card>
          <Card title={t('أفضل قياس تالي', 'Next-best measurement')} sub={t('أكثر معلومة لكل ساعة', 'Most information per hour')}>
            <NextBest />
          </Card>
        </div>
      </div>
    </div>
  );
}
