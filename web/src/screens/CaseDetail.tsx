import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Plot from '@observablehq/plot';
import { api, ApiError, post } from '../api';
import { useStore, useT } from '../store';
import { go } from '../route';
import { centroid, MapView } from '../MapView';
import { Badge, Card, ErrorState, LayerTag, Loading, Num, ProbBar } from '../ui';
import { useMapCases, useRouteGeo } from './Overview';
import type { Interval } from '../fmt';

const OUTCOMES: { id: string; ar: string; en: string; tone: string }[] = [
  { id: 'anomaly_found_connection', ar: 'لقينا توصيلة', en: 'Connection found', tone: 'amber' },
  { id: 'anomaly_found_leak', ar: 'لقينا تسريب', en: 'Leak found', tone: 'amber' },
  { id: 'no_anomaly_found', ar: 'ما لقينا إشي', en: 'No anomaly found', tone: 'teal' },
  { id: 'inconclusive', ar: 'غير حاسم', en: 'Inconclusive', tone: 'grey' },
];

function FusionCard({ id }: { id: string }) {
  const t = useT();
  const q = useQuery({ queryKey: ['fusion', id], queryFn: () => api(`/api/cases/${encodeURIComponent(id)}/fusion`) });
  if (q.isLoading) return <Card title={t('الدمج', 'Fusion')}><Loading /></Card>;
  if (q.error) return <Card title={t('الدمج', 'Fusion')}><ErrorState error={q.error} what="fusion" /></Card>;
  const d = q.data;
  const rows: { key: string; ar: string; en: string; iv: Interval | null; tone: 'blue' | 'teal' | 'amber' }[] = [
    { key: 'line', ar: 'الخط وحده', en: 'Line only', iv: d.posterior_line_only, tone: 'blue' },
    { key: 'field', ar: 'الحقل وحده', en: 'Field only', iv: d.posterior_field_only, tone: 'teal' },
    { key: 'fused', ar: 'مدموج', en: 'Fused', iv: d.posterior_fused, tone: 'amber' },
  ];
  return (
    <Card title={t('لحظة الدمج: احتمال لاحق', 'The fusion moment: posterior')} sub={t('قبل أي نتيجة ميدانية', 'Before any field result')} right={<Badge label={d.label} />}>
      <div className="fusion">
        {rows.map((r) => (
          <div className={`fu-row ${r.key === 'fused' ? 'fu-fused' : ''}`} key={r.key}>
            <div className="fu-l">{r.ar} <span>· {r.en}</span></div>
            {r.iv ? (
              <>
                <ProbBar iv={r.iv} prior={d.prior} tone={r.tone} />
                <div className="fu-v"><Num iv={r.iv} label={d.label} badge={false} /></div>
              </>
            ) : <div className="fu-none">{t('ما في إشارة من هالنوع', 'No signal of this kind')}</div>}
          </div>
        ))}
        <div className="fu-prior muted small">
          {t('الاحتمال المسبق (افتراض)', 'Prior (assumption)')}: <bdi dir="ltr" className="num">{d.prior}</bdi> <span className="pb-prior-key" /> · <Badge label="Hypothesis" compact />
        </div>
      </div>
      <h3 className="h3">{t('الإشارات', 'Signals')} <span className="muted small">· LR = {t('نسبة الأرجحية', 'likelihood ratio')}</span></h3>
      <ul className="signals">
        {d.signals.map((s: any) => (
          <li key={s.evidence_id} className="sig">
            <div className="sig-h"><LayerTag layer={s.layer} /> <Badge label={s.label} /> <span className="mono muted" dir="ltr">{s.evidence_id}</span></div>
            <div className="sig-t" dir="auto">{s.signal}</div>
            <div className="sig-n">LR <Num iv={s.lr} label={s.label} badge={false} />{typeof s.imbalance_m3h === 'number' && <span className="muted"> · {t('عدم توازن', 'imbalance')} <bdi dir="ltr" className="num">{s.imbalance_m3h} m³/h</bdi> <span className="point-tag">{t('نقطي', 'point')}</span></span>}</div>
          </li>
        ))}
      </ul>
      {d.note && <p className="muted small">{t('نسب الأرجحية غير معايرة لحد ما تتوفر نتائج ميدانية حقيقية.', d.note)}</p>}
    </Card>
  );
}

function NdviChart({ series, year }: { series: any[]; year: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const p = Plot.plot({
      width: 460, height: 190, marginLeft: 40, marginBottom: 30,
      style: { fontFamily: 'Readex Pro Variable, sans-serif', fontSize: '11px', background: 'transparent' },
      x: { label: null, tickFormat: (d: number) => String(d), ticks: series.map((s) => s.year) },
      y: { label: 'NDVI', domain: [0, 1], grid: true },
      marks: [
        Plot.ruleX([year], { stroke: '#B45309', strokeDasharray: '3,3' }),
        Plot.areaY(series, { x: 'year', y: 'green_fraction', fill: '#0F766E', fillOpacity: 0.08 }),
        Plot.lineY(series, { x: 'year', y: 'ndvi_mean', stroke: '#0F766E', strokeWidth: 2 }),
        Plot.dot(series, { x: 'year', y: 'ndvi_mean', fill: (d: any) => (d.year === year ? '#B45309' : '#0F766E'), r: 3.5 }),
      ],
    });
    ref.current.replaceChildren(p);
    return () => p.remove();
  }, [series, year]);
  return <div ref={ref} className="plot" dir="ltr" />;
}

function FieldEvidence({ fieldId, cropland }: { fieldId: string; cropland: boolean }) {
  const t = useT();
  const ts = useQuery({ queryKey: ['ts', fieldId], queryFn: () => api(`/api/fields/${encodeURIComponent(fieldId)}/timeseries`) });
  const chips = useQuery({ queryKey: ['chips', fieldId], queryFn: () => api(`/api/fields/${encodeURIComponent(fieldId)}/chips`) });
  const years: { year: number; url: string }[] = useMemo(() => {
    if (chips.data?.years?.length) return chips.data.years;
    // documented static fallback: /chips/<field_id>_<year>.png
    if (ts.data?.series) return ts.data.series.map((s: any) => ({ year: s.year, url: `/chips/${fieldId}_${s.year}.png` }));
    return [];
  }, [chips.data, ts.data, fieldId]);
  const [idx, setIdx] = useState<number | null>(null);
  const cur = years.length ? years[idx ?? years.length - 1] : null;
  const first = years[0];
  const row = ts.data?.series?.find((s: any) => s.year === cur?.year);
  return (
    <Card title={<>{t('دليل القمر الصناعي', 'Satellite evidence')} · <bdi dir="ltr">{fieldId}</bdi></>} sub="Sentinel-2 · NDVI" right={<Badge label={ts.data?.label ?? chips.data?.label ?? 'Observed'} />}>
      {cropland && <div className="caveat-line" role="note"><b>داخل أرض زراعية قائمة · inside existing cropland</b> <span>{t('الخضرة الجديدة غالباً دورة زراعية، مش بالضرورة سحب غير مرخّص', 'new greenness is likely crop rotation, not necessarily unlicensed abstraction')} · WorldCover</span></div>}
      {ts.error && <ErrorState error={ts.error} what="timeseries" />}
      {years.length > 0 && cur && (
        <>
          <div className="chips">
            <figure>
              <img src={first.url} alt={`${fieldId} ${first.year}`} />
              <figcaption>{t('قبل', 'Before')} · <bdi dir="ltr">{first.year}</bdi></figcaption>
            </figure>
            <figure>
              <img src={cur.url} alt={`${fieldId} ${cur.year}`} />
              <figcaption>{t('بعد', 'After')} · <bdi dir="ltr">{cur.year}</bdi>{row && <> · NDVI <bdi dir="ltr" className="num">{row.ndvi_mean.toFixed(2)}</bdi></>}</figcaption>
            </figure>
          </div>
          <div className="slider" dir="ltr">
            <span className="mono">{first.year}</span>
            <input type="range" min={0} max={years.length - 1} step={1} value={idx ?? years.length - 1} onChange={(e) => setIdx(Number(e.target.value))} aria-label="year" />
            <span className="mono">{years[years.length - 1].year}</span>
          </div>
        </>
      )}
      {ts.data?.series && cur && <NdviChart series={ts.data.series} year={cur.year} />}
      <p className="muted small">{t('الخط: متوسط NDVI بموسم الجفاف. المساحة المظللة: نسبة البكسلات الخضراء. Sentinel-2 يشوف استخدام المياه السطحي بس.', 'Line: dry-season mean NDVI. Shaded: green pixel fraction. Sentinel-2 sees surface water use only.')}</p>
    </Card>
  );
}

function VerifyCard({ id, caseData }: { id: string; caseData: any }) {
  const t = useT();
  const qc = useQueryClient();
  const user = useStore((s) => s.user);
  const [before, setBefore] = useState<Interval | null>(null);
  const m = useMutation({
    mutationFn: (outcome: string) => { setBefore(caseData?.p ?? null); return post('/api/field-results', { case_id: id, outcome }); },
    onSuccess: () => {
      ['queue', 'case', 'map-cases', 'impact', 'next-best', 'explain'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
  });
  const r = m.data;
  const canPost = user && ['engineer', 'inspector'].includes(user.role);
  return (
    <Card title={t('تحقّق: نتيجة الزيارة', 'Verify: field result')} sub={t('الطاقم يرجع بنتيجة، والاحتمال يتحدّث والقائمة تنعاد', 'The crew reports back; the posterior updates and the queue re-ranks')}
      right={<span className="demo-tag"><Badge label="Simulated" compact /> {t('إدخال تجريبي', 'Simulated demo entry')}</span>}>
      <div className="outcomes">
        {OUTCOMES.map((o) => (
          <button key={o.id} className={`btn outcome tone-${o.tone}`} disabled={!canPost || m.isPending} onClick={() => m.mutate(o.id)} data-outcome={o.id}>
            <b>{o.ar}</b><span>{o.en}</span>
          </button>
        ))}
      </div>
      {!canPost && <p className="muted small">{t('هذا الدور ما بقدر يدخل نتائج ميدانية.', 'This role cannot submit field results.')}</p>}
      {m.isPending && <Loading text={t('جارِ التحديث…', 'Updating…')} />}
      {m.error && <ErrorState error={m.error} what="field-results" />}
      {r && (
        <div className="fr-result" key={r.result_id}>
          <div className="fr-tag">«{t('إدخال تجريبي', 'Simulated demo entry')} · Simulated demo entry» <span className="mono" dir="ltr">{r.result_id} · {r.evidence_id}</span></div>
          <div className="fr-grid">
            <div className="fr-cell">
              <div className="fr-l">{t('الترتيب', 'Rank')}</div>
              <div className="fr-big" dir="ltr"><span className="was">#{r.rank_before}</span> <span className="arrow">→</span> <span className="now anim-pop">#{r.rank_after}</span></div>
            </div>
            <div className="fr-cell wide">
              <div className="fr-l">{t('الاحتمال اللاحق', 'Posterior')} <Badge label="Hypothesis" compact /></div>
              <ProbBar iv={r.p_after} animateFrom={before} tone="amber" />
              <div className="fr-nums" dir="ltr">
                {before ? <Num iv={before} label="Hypothesis" badge={false} /> : <bdi className="num">{r.posterior_before}</bdi>}
                <span className="arrow">→</span>
                <Num iv={r.p_after} label="Hypothesis" badge={false} />
              </div>
            </div>
          </div>
          <p className="muted small">{t('القائمة انعاد ترتيبها من الخادم.', 'The queue was re-fetched from the server.')} <a href="#/overview">{t('شوف القائمة', 'See the queue')}</a></p>
        </div>
      )}
    </Card>
  );
}

export function CaseDetail({ id }: { id: string }) {
  const t = useT();
  const select = useStore((s) => s.select);
  const user = useStore((s) => s.user);
  const qc = useQueryClient();
  useEffect(() => { select(id); }, [id]);
  const c = useQuery({ queryKey: ['case', id], queryFn: () => api(`/api/cases/${encodeURIComponent(id)}`) });
  const ex = useQuery({ queryKey: ['explain', id], queryFn: () => api(`/api/cases/${encodeURIComponent(id)}/explain`) });
  const fu = useQuery({ queryKey: ['fusion', id], queryFn: () => api(`/api/cases/${encodeURIComponent(id)}/fusion`) });
  const cases = useMapCases();
  const route = useRouteGeo();
  const [editMsg, setEditMsg] = useState<string | null>(null);

  const signals: any[] = fu.data?.signals ?? ex.data?.layer_contributions ?? [];
  const isField = (c.data && id.includes('-F-')) || cases.data?.features?.find((f: any) => f.properties.case_id === id)?.properties.layer === 'source';
  const linkedField = useMemo(() => {
    if (isField) return id;
    const s = signals.find((x) => x.layer === 'source');
    const m = s?.signal?.match(/KRK-F-\d+/);
    return m?.[0] ?? ex.data?.linked_case_ids?.find((x: string) => x.includes('-F-')) ?? null;
  }, [isField, signals, ex.data, id]);
  const cropland = signals.some((s) => s.layer === 'source' && /cropland/i.test(s.signal ?? ''));

  async function proposeEdit() {
    setEditMsg(null);
    const f = cases.data?.features?.find((x: any) => x.properties.case_id === id);
    if (!f) { setEditMsg('no geometry for case'); return; }
    const [lon, lat] = centroid(f.geometry);
    try {
      const r = await post('/api/map-edits', { case_id: id, kind: 'tap_location', geometry: { type: 'Point', coordinates: [lon, lat] }, evidence_ids: c.data?.evidence_ids ?? [] });
      qc.invalidateQueries({ queryKey: ['map-edits'] });
      setEditMsg(`${r.edit_id} · ${r.status}`);
    } catch (e) { setEditMsg(`HTTP ${(e as ApiError).status} · ${(e as Error).message}`); }
  }

  if (c.isLoading) return <Loading />;
  if (c.error) return <div className="page"><ErrorState error={c.error} what={id} /></div>;
  const d = c.data;
  const focus = [id, ...(ex.data?.linked_case_ids ?? [])];
  return (
    <div className="page">
      <div className="page-h case-h">
        <div>
          <div className="crumbs"><a href="#/overview">{t('نظرة عامة', 'Overview')}</a> / {t('حالة', 'Case')}</div>
          <h1><bdi dir="ltr">{id}</bdi> <span className="rank-pill">#{d.rank}</span> {isField !== undefined && <LayerTag layer={isField ? 'source' : 'transmission'} />}</h1>
          <p className="lede">{t('مرشّح للتفتيش — مش مخالفة ولا سرقة. الرقم فرضية لحد ما الطاقم يتحقق.', 'A candidate for inspection — not a violation or theft. A hypothesis until the crew verifies.')}</p>
        </div>
        <div className="case-kpis">
          <div className="kpi"><div className="kpi-l">{t('م³ لكل ساعة تفتيش', 'm³ per inspection hour')}</div><Num iv={d.m3_per_insp_hour} unit="m³/day/h" label={d.label} /></div>
          <div className="kpi"><div className="kpi-l">{t('الاحتمال', 'Probability')}</div><Num iv={d.p} label={d.label} /></div>
          <div className="kpi"><div className="kpi-l">{t('الحجم', 'Volume')}</div><Num iv={d.volume_m3_day} unit="m³/day" label={d.label} /></div>
        </div>
      </div>
      <div className="case-actions">
        {user?.role === 'engineer' && <button className="btn" onClick={() => go(`#/work-orders?case=${encodeURIComponent(id)}`)}>{t('أمر عمل جديد', 'New work order')}</button>}
        {user && ['engineer', 'inspector'].includes(user.role) && <button className="btn" onClick={proposeEdit}>{t('اقترح تعديل خريطة', 'Propose map edit')}</button>}
        {editMsg && <span className="mono small" dir="ltr">{editMsg}</span>}
        <span className="muted small">{t('الأدلة', 'Evidence')}: <span className="mono" dir="ltr">{(d.evidence_ids ?? []).join(', ')}</span></span>
      </div>
      <div className="case-grid">
        <div className="col">
          <FusionCard id={id} />
          <VerifyCard id={id} caseData={d} />
        </div>
        <div className="col">
          {linkedField ? <FieldEvidence fieldId={linkedField} cropland={cropland} /> : <Card title={t('دليل القمر الصناعي', 'Satellite evidence')}><p className="muted">{t('ما في حقل مرتبط', 'No linked field')}</p></Card>}
          <Card title={t('الموقع', 'Location')} sub={t('الحالة والحقول المرتبطة', 'Case and linked fields')}>
            <MapView cases={cases.data} route={route.data} selected={id} focus={focus} onSelect={(x) => go(`#/case/${encodeURIComponent(x)}`)} height={300} />
            {ex.data?.linked_case_ids?.length > 0 && (
              <div className="linked">{t('مرتبطة', 'Linked')}: {ex.data.linked_case_ids.map((x: string) => <a key={x} href={`#/case/${encodeURIComponent(x)}`} className="mono chip" dir="ltr">{x}</a>)}</div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
