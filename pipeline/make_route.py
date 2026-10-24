"""Build the APPROXIMATE main-line route for Blue Balance -> data/processed/route.geojson.

The real transmission-pipeline geometry is restricted, so the route is approximated by
the Desert Highway (Highway 15) through Qatraneh, which the main line follows. Method:

1. Query OpenStreetMap through the Overpass API with curl (python's urllib SSL store has
   an expired certificate on the build machine), retrying across several endpoints.
2. Merge the returned ways into one LineString clipped to the AOI (longest merged part).
3. If every endpoint fails, fall back to a polyline hand-traced from the 2026 Sentinel-2
   scene (FALLBACK_LONLAT below); the `source` property then says so.

The output is labelled "Simulated": it is an approximate route, not surveyed pipe geometry.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, box, mapping
from shapely.ops import linemerge, unary_union

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "processed" / "route.geojson"
CACHE = REPO / "data" / "processed" / "osm_highway15_raw.json"

AOI = (35.86, 31.15, 36.14, 31.32)  # lon_min, lat_min, lon_max, lat_max
QUERY = (
    '[out:json][timeout:60];'
    'way["highway"~"trunk|primary|motorway"]["ref"~"15"]'
    f'({AOI[1]},{AOI[0]},{AOI[3]},{AOI[2]});out geom;'
)
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
ATTEMPTS_PER_ENDPOINT = 3
BACKOFF_S = 8
USER_AGENT = "BlueBalance-hackathon/0.1 (Hacktoberfest Hack Day Amman)"

# Fallback only: hand-traced vertices (lon, lat). Filled in from the 2026 S2 scene if used.
FALLBACK_LONLAT: list[tuple[float, float]] = []

PROPS = {
    "label": "Simulated",
    "name_en": "Approximate route",
    "name_ar": "مسار تقريبي",
}


def fetch_overpass() -> tuple[dict | None, str | None, list[str]]:
    """Return (overpass_json, endpoint_used, error_log)."""
    errors: list[str] = []
    for attempt in range(ATTEMPTS_PER_ENDPOINT):
        for ep in ENDPOINTS:
            cmd = ["curl", "-s", "-m", "90", "-A", USER_AGENT,
                   "--data-urlencode", f"data={QUERY}", ep]
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=120)
            except subprocess.TimeoutExpired:
                errors.append(f"{ep}: subprocess timeout")
                continue
            body = res.stdout.decode("utf-8", errors="replace")
            if res.returncode != 0:
                errors.append(f"{ep}: curl rc={res.returncode}")
                continue
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                errors.append(f"{ep}: non-JSON reply ({body[:60].strip()!r})")
                continue
            if data.get("elements"):
                return data, ep, errors
            errors.append(f"{ep}: JSON with 0 elements")
        time.sleep(BACKOFF_S * (2 ** attempt))
    return None, None, errors


def merge_ways(data: dict) -> LineString:
    lines = []
    for el in data["elements"]:
        if el.get("type") == "way" and el.get("geometry"):
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) >= 2:
                lines.append(LineString(coords))
    # Dual carriageways come back as two parallel ways; merging keeps the connected chains
    # and we keep the longest one that lies inside the AOI.
    merged = linemerge(unary_union(lines)).intersection(box(*AOI))
    if isinstance(merged, LineString):
        return merged
    parts = [g for g in getattr(merged, "geoms", []) if isinstance(g, LineString)]
    if not parts:
        raise ValueError("Overpass ways did not merge into a line inside the AOI")
    return max(parts, key=lambda g: g.length)


def main() -> int:
    data, ep, errors = fetch_overpass()
    if data is not None:
        CACHE.write_text(json.dumps(data), encoding="utf-8")
        line = merge_ways(data)
        props = {**PROPS,
                 "source": "OpenStreetMap contributors, ODbL (Overpass API, Highway 15 ways)",
                 "method": "osm_overpass",
                 "endpoint": ep,
                 "n_ways": sum(1 for e in data["elements"] if e.get("type") == "way")}
    elif FALLBACK_LONLAT:
        line = LineString(FALLBACK_LONLAT)
        props = {**PROPS, "source": "hand-traced from Sentinel-2 (2026-08-24 scene)",
                 "method": "hand_traced_s2"}
    else:
        print("Overpass failed and no fallback polyline is set:\n  " + "\n  ".join(errors))
        return 1
    props["overpass_errors"] = errors
    props["length_deg"] = round(line.length, 6)
    fc = {"type": "FeatureCollection",
          "features": [{"type": "Feature", "properties": props, "geometry": mapping(line)}]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"route: {props['method']} with {len(line.coords)} vertices -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
