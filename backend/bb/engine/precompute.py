"""Precompute the Layer 2 segment twins -> data/processed/segments.json.

    python -m bb.engine.precompute [--route PATH] [--fields PATH] [--out PATH]

- Splits the route into ~5 km segments between ASSUMED meter points (KRK-T-001 ...).
- Injects ONE simulated tap (25 m3/h, ASSUMED demo size) in the segment nearest the highest-baseline_score
  field: this is the demo's fusion case, labelled Simulated. Every other segment has no tap.
- Simulates every segment in WNTR with seeded meter noise; computes lr_line, the tap estimate and
  evidence_id EV-TWIN-####. Twin outputs are Simulated; posteriors are Hypothesis; nothing is Field-verified.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import substring, transform

from bb import config

from . import energy, fusion, learning, nextbest, priority, twin, volume

ASSUMPTIONS = {
    "segment_length_m": {"value": 5000.0, "source": "ASSUMED",
                         "note": "Meter points assumed every ~5 km; the route is split into equal segments of about this length."},
    "demo_tap_m3h": {"value": 25.0, "source": "ASSUMED",
                     "note": "Simulated tap injected only in the fusion-case segment (~6.9 L/s, inside the A4 1-20 L/s grid)."},
    "field_near_m": {"value": 1000.0, "source": "ASSUMED",
                     "note": "A field counts as 'next to' a segment within this distance."},
    "base_seed": {"value": 20261024, "source": "method", "note": "Meter-noise seed = base_seed + segment index."},
    "crs_metric": {"value": "EPSG:32636", "source": "method", "note": "UTM 36N for metric lengths/distances."},
}

_FWD = Transformer.from_crs("EPSG:4326", "EPSG:32636", always_xy=True).transform
_INV = Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True).transform


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _route_line(gj: dict) -> LineString:
    feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
    for ft in feats:
        geom = shape(ft["geometry"] if "geometry" in ft else ft)
        if geom.geom_type == "LineString":
            return geom
        if geom.geom_type == "MultiLineString":
            return max(geom.geoms, key=lambda g: g.length)
    raise ValueError("route.geojson has no LineString")


def _fields(gj: dict) -> list[dict]:
    out = []
    for ft in gj.get("features", []):
        props = dict(ft.get("properties") or {})
        geom = shape(ft["geometry"])
        c = props.get("centroid")
        pt = Point(c[0], c[1]) if c else geom.centroid
        out.append({"props": props, "pt_m": transform(_FWD, pt)})
    return out


def _iv3(d: dict) -> dict:
    return {k: d[k] for k in ("mean", "lo", "hi")}


def build(route_gj: dict, fields_gj: dict) -> dict:
    line_m = transform(_FWD, _route_line(route_gj))
    total = line_m.length
    seg_len = ASSUMPTIONS["segment_length_m"]["value"]
    n = max(1, round(total / seg_len))
    pieces = [substring(line_m, total * i / n, total * (i + 1) / n) for i in range(n)]
    fields = _fields(fields_gj)

    fusion_idx, top = None, None
    scored = [f for f in fields if f["props"].get("baseline_score") is not None]
    if scored:
        top = max(scored, key=lambda f: float(f["props"]["baseline_score"]))
        fusion_idx = min(range(n), key=lambda i: pieces[i].distance(top["pt_m"]))

    D = twin.ASSUMPTIONS["diameter_m"]["value"]
    C = twin.ASSUMPTIONS["roughness_c"]["value"]
    Q = twin.ASSUMPTIONS["inflow_m3h"]["value"]
    err = twin.ASSUMPTIONS["meter_error_frac"]["value"]
    tap_prior = tuple(twin.ASSUMPTIONS["tap_prior_m3h"]["value"])
    prior = fusion.ASSUMPTIONS["prior_tap_per_segment"]["value"]
    near = ASSUMPTIONS["field_near_m"]["value"]

    segments = []
    for i, piece in enumerate(pieces):
        injected = i == fusion_idx
        tap = ASSUMPTIONS["demo_tap_m3h"]["value"] if injected else 0.0
        sim = twin.simulate_segment(piece.length, D, C, Q, tap, err, ASSUMPTIONS["base_seed"]["value"] + i)
        lr = twin.lr_line(sim["imbalance_m3h"], sim["meter_sigma_m3h"], tap_prior)
        est = twin.estimate_tap_m3h(sim["imbalance_m3h"], sim["meter_sigma_m3h"])
        geom_ll = transform(_INV, piece)
        nearby = sorted(
            ({"field_id": f["props"].get("field_id"), "dist_m": float(piece.distance(f["pt_m"])),
              "baseline_score": f["props"].get("baseline_score")} for f in fields
             if piece.distance(f["pt_m"]) <= near or (injected and f is top)),
            key=lambda r: r["dist_m"])
        seg = {
            "segment_id": f"KRK-T-{i + 1:03d}",
            "evidence_id": f"EV-TWIN-{i + 1:04d}",
            "geometry": {"type": "LineString", "coordinates": [[round(x, 6), round(y, 6)] for x, y in geom_ll.coords]},
            "length_m": float(piece.length),
            "meters": {"upstream": f"FM-{i:02d}", "downstream": f"FM-{i + 1:02d}", "label": "Simulated",
                       "note": "Meter points are ASSUMED locations"},
            "inflow_m3h": sim["inflow_m3h"],
            "outflow_m3h": sim["outflow_m3h"],
            "imbalance_m3h": sim["imbalance_m3h"],
            "meter_sigma_m3h": sim["meter_sigma_m3h"],
            "pressure_drop_m": sim["pressure_drop_m"],
            "velocity_m_s": sim["velocity_m_s"],
            "seed": sim["seed"],
            "solver": sim["solver"],
            "lr_line": _iv3(lr),
            "lr_line_log10": lr["log10_mean"],
            "tap_estimate_m3h": _iv3(est),
            "tap_injected": injected,
            "tap_injected_m3h": tap,
            "posterior_line_only": _iv3(fusion.posterior(prior, [lr])),
            "nearby_fields": nearby,
            "label": "Simulated",
            "label_posterior": "Hypothesis",
        }
        if injected and top is not None:
            score = float(top["props"]["baseline_score"])
            lrf = fusion.lr_field(score)
            p_line = fusion.posterior(prior, [lr])
            p_field = fusion.posterior(prior, [lrf])
            p_fused = fusion.posterior(prior, [lr, lrf])
            vol = {k: v * 24.0 for k, v in _iv3(est).items()}  # m3/h -> m3/day, constant tap ASSUMED
            th = priority.ASSUMPTIONS["travel_h_default"]["value"]
            ih = priority.ASSUMPTIONS["inspect_h"]["value"]
            seg["fusion"] = {
                "field_id": top["props"].get("field_id"),
                "field_evidence_id": top["props"].get("evidence_id"),
                "field_dist_m": float(piece.distance(top["pt_m"])),
                "baseline_score": score,
                "lr_field": _iv3(lrf),
                "prior": prior,
                "posterior_line_only": _iv3(p_line),
                "posterior_field_only": _iv3(p_field),
                "posterior_fused": _iv3(p_fused),
                "volume_m3_day": vol,
                "expected_m3_day": _iv3(priority.expected_m3_day(p_fused, vol)),
                "m3_per_inspection_hour": _iv3(priority.m3_per_inspection_hour(p_fused, vol, th, ih)),
                "travel_h": th, "inspect_h": ih,
                "label": "Hypothesis",
                "note": "Tap is Simulated (injected for the demo). Candidate = inspection priority, never a violation.",
            }
        segments.append(seg)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "region_id": config.REGION_ID,
        "label": "Simulated",
        "route_length_m": float(total),
        "fusion_case_id": segments[fusion_idx]["segment_id"] if fusion_idx is not None else None,
        "segments": segments,
        "assumptions": {
            "twin": twin.ASSUMPTIONS, "fusion": fusion.ASSUMPTIONS, "priority": priority.ASSUMPTIONS,
            "volume": volume.ASSUMPTIONS, "energy": energy.ASSUMPTIONS, "learning": learning.DETECTION,
            "nextbest": {**nextbest.ASSUMPTIONS, "catalogue_items": nextbest.CATALOGUE},
            "precompute": ASSUMPTIONS,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Precompute Blue Balance segment twins (Simulated).")
    ap.add_argument("--route", type=Path, default=config.PROCESSED / "route.geojson")
    ap.add_argument("--fields", type=Path, default=config.PROCESSED / "fields.geojson")
    ap.add_argument("--out", type=Path, default=config.PROCESSED / "segments.json")
    a = ap.parse_args(argv)
    missing = [str(p) for p in (a.route, a.fields) if not p.exists()]
    if missing:
        print("precompute: missing input file(s): " + ", ".join(missing)
              + "\nThe DATA agent produces route.geojson and fields.geojson in data/processed/. Nothing written.",
              file=sys.stderr)
        return 2
    result = build(_load(a.route), _load(a.fields))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, allow_nan=False)
    print(f"precompute: wrote {len(result['segments'])} segments to {a.out}; fusion case = {result['fusion_case_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
