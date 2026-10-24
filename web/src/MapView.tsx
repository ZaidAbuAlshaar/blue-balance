import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

// Bundled worker (the default lookup next to import.meta.url breaks after bundling).
maplibregl.setWorkerUrl(workerUrl);

type FC = { type: 'FeatureCollection'; features: any[] };

// Offline plain style: background only. No tiles, no glyphs, no sprites.
const STYLE: any = {
  version: 8,
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#E9EDF1' } }],
};

const P_COLOR: any = ['interpolate', ['linear'], ['get', 'p_mean'], 0, '#9AA8B6', 0.25, '#1D6FA3', 0.6, '#B45309', 0.9, '#8A3A06'];

function coordsOf(g: any): number[][] {
  const out: number[][] = [];
  const walk = (c: any) => { if (typeof c[0] === 'number') out.push(c); else c.forEach(walk); };
  walk(g.coordinates);
  return out;
}
export function centroid(g: any): [number, number] {
  const cs = coordsOf(g);
  const s = cs.reduce((a, c) => [a[0] + c[0], a[1] + c[1]], [0, 0]);
  return [s[0] / cs.length, s[1] / cs.length];
}
function bboxOf(features: any[]): [[number, number], [number, number]] | null {
  const cs = features.flatMap((f) => coordsOf(f.geometry));
  if (!cs.length) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  cs.forEach(([x, y]) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); });
  return [[x0, y0], [x1, y1]];
}

export function MapView({ cases, route, selected, onSelect, focus, height = 460 }: {
  cases?: FC; route?: FC; selected?: string | null; onSelect?: (id: string) => void; focus?: string[]; height?: number;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const ready = useRef(false);
  const bound = useRef(false);
  const cb = useRef(onSelect);
  cb.current = onSelect;
  const props = useRef({ cases, route, selected, focus });
  props.current = { cases, route, selected, focus };

  function sel() {
    const m = map.current;
    const s = props.current.selected ?? '';
    if (!m || !ready.current || !m.getLayer('segs-sel')) return;
    m.setFilter('segs-sel', ['==', ['get', 'case_id'], s]);
    m.setFilter('fieldpts-sel', ['==', ['get', 'case_id'], s]);
    markers.current.forEach((k) => {
      const e = k.getElement();
      if (e.dataset.case) e.classList.toggle('sel', e.dataset.case === s);
    });
  }

  /** Hide a case label when it would overlap a higher-ranked one (no glyph collision engine offline). */
  function declutter() {
    const m = map.current;
    if (!m) return;
    const shown: DOMRect[] = [];
    markers.current.filter((k) => k.getElement().dataset.rank).sort((a, b) => Number(a.getElement().dataset.rank) - Number(b.getElement().dataset.rank)).forEach((k) => {
      const e = k.getElement();
      e.style.visibility = 'visible';
      const r = e.getBoundingClientRect();
      const hit = shown.some((o) => !(r.right < o.left || r.left > o.right || r.bottom < o.top || r.top > o.bottom));
      if (hit && e.dataset.case !== props.current.selected) e.style.visibility = 'hidden'; else shown.push(r);
    });
  }

  function draw() {
    const m = map.current;
    const { cases, route, focus } = props.current;
    if (!m || !ready.current) return;
    markers.current.forEach((k) => k.remove());
    markers.current = [];
    if (route) {
      const src = m.getSource('route') as maplibregl.GeoJSONSource | undefined;
      if (src) src.setData(route as any);
      else {
        m.addSource('route', { type: 'geojson', data: route as any });
        m.addLayer({ id: 'route', type: 'line', source: 'route', paint: { 'line-color': '#5B6B7E', 'line-width': 2, 'line-dasharray': [3, 2] } });
      }
      const line = route.features[0]?.geometry?.coordinates;
      if (line?.length) {
        const mid = line[Math.floor(line.length * 0.15)];
        const div = document.createElement('div');
        div.className = 'map-label map-label-route';
        div.textContent = 'مسار تقريبي · Approximate route';
        markers.current.push(new maplibregl.Marker({ element: div, anchor: 'left', offset: [12, 0] }).setLngLat(mid).addTo(m));
      }
    }
    if (cases) {
      const segs = { type: 'FeatureCollection', features: cases.features.filter((f) => f.geometry.type.includes('LineString')) };
      const fields = { type: 'FeatureCollection', features: cases.features.filter((f) => f.geometry.type.includes('Polygon')) };
      const pts = { type: 'FeatureCollection', features: fields.features.map((f) => ({ type: 'Feature', properties: f.properties, geometry: { type: 'Point', coordinates: centroid(f.geometry) } })) };
      const put = (id: string, data: any) => {
        const s = m.getSource(id) as maplibregl.GeoJSONSource | undefined;
        if (s) s.setData(data); else m.addSource(id, { type: 'geojson', data });
      };
      put('segs', segs); put('fields', fields); put('fieldpts', pts);
      if (!m.getLayer('segs')) {
        m.addLayer({ id: 'segs-hit', type: 'line', source: 'segs', paint: { 'line-color': '#000', 'line-opacity': 0, 'line-width': 18 } });
        m.addLayer({ id: 'segs-sel', type: 'line', source: 'segs', paint: { 'line-color': '#0B1B3A', 'line-width': 12, 'line-opacity': 0.3 }, filter: ['==', ['get', 'case_id'], ''] });
        m.addLayer({ id: 'segs', type: 'line', source: 'segs', paint: { 'line-color': P_COLOR, 'line-width': 6 }, layout: { 'line-cap': 'round' } });
        m.addLayer({ id: 'fields-fill', type: 'fill', source: 'fields', paint: { 'fill-color': P_COLOR, 'fill-opacity': 0.12 } });
        m.addLayer({ id: 'fields-line', type: 'line', source: 'fields', paint: { 'line-color': P_COLOR, 'line-width': 1.6 } });
        m.addLayer({ id: 'fieldpts', type: 'circle', source: 'fieldpts', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 5, 15, 3], 'circle-color': '#ffffff', 'circle-stroke-color': P_COLOR, 'circle-stroke-width': 2.5 } });
        m.addLayer({ id: 'fieldpts-sel', type: 'circle', source: 'fieldpts', paint: { 'circle-radius': 11, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#0B1B3A', 'circle-stroke-width': 2 }, filter: ['==', ['get', 'case_id'], ''] });
        const layers = ['segs-hit', 'fields-fill', 'fieldpts'];
        layers.forEach((l) => {
          m.on('click', l, (e: any) => { const id = e.features?.[0]?.properties?.case_id; if (id) cb.current?.(id); });
          m.on('mouseenter', l, () => { m.getCanvas().style.cursor = 'pointer'; });
          m.on('mouseleave', l, () => { m.getCanvas().style.cursor = ''; });
        });
      }
      // HTML labels (no glyphs needed) for the top-ranked cases
      cases.features.filter((f) => f.properties.rank <= 5).forEach((f) => {
        const div = document.createElement('div');
        div.className = 'map-label map-label-case';
        div.dataset.case = f.properties.case_id;
        div.dataset.rank = String(f.properties.rank);
        div.innerHTML = `<b>#${f.properties.rank}</b> <span dir="ltr">${f.properties.case_id}</span>`;
        div.addEventListener('click', (ev) => { ev.stopPropagation(); cb.current?.(f.properties.case_id); });
        markers.current.push(new maplibregl.Marker({ element: div, anchor: 'bottom', offset: [0, -8] }).setLngLat(centroid(f.geometry)).addTo(m));
      });
      if (!bound.current || focus?.length) {
        const target = focus?.length ? cases.features.filter((f) => focus.includes(f.properties.case_id)) : [...cases.features, ...(route?.features ?? [])];
        const bb = bboxOf(target);
        if (bb) { m.fitBounds(bb, { padding: 56, maxZoom: focus?.length ? 14 : 13, duration: 0 }); bound.current = true; }
      }
    }
    sel();
    requestAnimationFrame(declutter);
  }

  useEffect(() => {
    if (!el.current) return;
    const m = new maplibregl.Map({ container: el.current, style: STYLE, center: [36.02, 31.2], zoom: 10, attributionControl: false });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
    m.on('load', () => { ready.current = true; draw(); });
    m.on('moveend', declutter);
    map.current = m;
    return () => { markers.current.forEach((k) => k.remove()); m.remove(); map.current = null; ready.current = false; bound.current = false; };
  }, []);

  useEffect(draw, [cases, route, focus?.join(',')]);
  useEffect(sel, [selected]);

  return (
    <div className="mapwrap" style={{ height }}>
      <div ref={el} className="map" />
      <div className="legend">
        <div className="lg-row"><span className="lg-dash" /> مسار تقريبي · Approximate route</div>
        <div className="lg-row"><span className="lg-ramp" /> <span>p_mean</span> <span dir="ltr" className="mono">0 → 1</span></div>
        <div className="lg-row"><span className="lg-ring" /> حقل · field (outline)</div>
      </div>
    </div>
  );
}
