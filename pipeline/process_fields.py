"""Layer 1 ("source") of Blue Balance: newly irrigated green patches near the main line.

Inputs (E:\\blue-balance-data\\raw, see raw/manifest.json):
  s2/s2_<date>_<band>.tif   Sentinel-2 L2A, one dry-season scene per year 2017-2026, EPSG:32636, 10 m
  worldcover_2021.tif       ESA WorldCover 2021 (class 40 = cropland), same grid
  open_meteo_era5_daily.json  ERA5 daily precipitation_sum and et0_fao_evapotranspiration
Also reads data/processed/route.geojson (run pipeline/make_route.py first).

Outputs (data/processed/): fields.geojson, field_timeseries.json, chips/<field_id>_<year>.png,
manifest.json.

Method (all thresholds are constants below and are copied into manifest.json):
  * Reflectance = (DN - 1000)/10000 for processing baseline >= 04.00 (BOA_ADD_OFFSET),
    DN/10000 before. Pixels with SCL in {0,1,3,8,9,10} or NaN are invalid.
  * NDVI = (B08 - B04)/(B08 + B04); green = NDVI > GREEN_NDVI on valid pixels.
  * New green = green in both NEW_YEARS, valid and not green in any valid OLD_YEARS scene
    (at least one OLD_YEARS scene must be valid). Cleaned with a binary opening, components
    >= MIN_PIXELS kept, polygonised and reprojected to WGS84.
  * Features are normalised to [0, 1] and combined with the team's expert-prior weights into
    baseline_score. Measured values are "Observed"; the score is a "Hypothesis".
Candidates are places worth an inspection visit, never violations.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw
from pyproj import Transformer
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform, unary_union

REPO = Path(__file__).resolve().parents[1]
RAW = Path(r"E:\blue-balance-data\raw")
S2 = RAW / "s2"
OUT = REPO / "data" / "processed"
CHIPS = OUT / "chips"

CRS = "EPSG:32636"
PIXEL_M = 10.0
SCL_INVALID = (0, 1, 3, 8, 9, 10)  # nodata, saturated/defective, cloud shadow, cloud med/high, cirrus
OFFSET_BASELINE = (4, 0)           # baseline >= 04.00 carries BOA_ADD_OFFSET = -1000
BOA_OFFSET_DN = 1000.0
QUANT = 10000.0

GREEN_NDVI = 0.30          # desert background NDVI p99 is 0.10-0.14 in every scene (see manifest)
OLD_YEARS = (2017, 2018)
NEW_YEARS = (2025, 2026)
PERSIST_YEARS = (2023, 2024, 2025, 2026)
PATCH_GREEN_FRACTION = 0.5  # a patch "is green" in a year when >= 50 % of its valid pixels are green
OPEN_STRUCT = ndimage.generate_binary_structure(2, 1)  # 3x3 cross, one iteration
MIN_PIXELS = 20             # 2,000 m2
WORLDCOVER_CROPLAND = 40
TOP_N = 25
TOP_CHIPS = 10
CHIP_HALF_PX = 64           # 128 px * 10 m = 1.28 km box, upsampled to 256x256
CHIP_SIZE = 256
STRETCH_PCT = (0.1, 99.9)  # wide: desert dominates the pool and 2-98 crushes fields to black

# Normalisation caps
PROX_CAP_M = 5000.0
ISO_CAP_M = 2000.0
NDVI_INC_CAP = 0.4
SIZE_MIN_M2 = MIN_PIXELS * PIXEL_M ** 2  # 2,000 m2 -> f_small_size = 1
SIZE_CAP_M2 = 100_000.0                  # 10 ha -> f_small_size = 0 (log scale in between)
WEIGHTS = {"f_proximity": 0.30, "f_isolation": 0.25, "f_ndvi_increase": 0.20,
           "f_persistence": 0.15, "f_small_size": 0.10}
DRY_MONTHS = (6, 7, 8, 9)
ANOMALY_GREEN_RATIO = 3.0   # scene flagged if its AOI green fraction > 3x the median year

LICENCES = {
    "sentinel-2": "Contains modified Copernicus Sentinel data (2017-2026), free and open with attribution",
    "esa-worldcover": "ESA WorldCover 10 m 2021 v200, CC-BY-4.0",
    "era5-open-meteo": "ERA5 reanalysis via Open-Meteo archive API, CC BY 4.0",
}


def baseline_tuple(s: str) -> tuple[int, int]:
    a, b = s.split(".")
    return int(a), int(b)


def needs_offset(baselines: list[str]) -> bool:
    flags = {baseline_tuple(b) >= OFFSET_BASELINE for b in baselines}
    if len(flags) != 1:
        raise ValueError(f"scene mixes pre- and post-04.00 baselines: {baselines}")
    return flags.pop()


def read_band(d: str, band: str, window=None) -> np.ndarray:
    with rasterio.open(S2 / f"s2_{d}_{band}.tif") as src:
        return src.read(1, window=window).astype(np.float32)


def reflectance(dn: np.ndarray, offset: bool) -> np.ndarray:
    return (dn - BOA_OFFSET_DN) / QUANT if offset else dn / QUANT


def load_year(scene: dict) -> dict:
    d = scene["date"]
    off = needs_offset(scene["processing_baseline"])
    red = reflectance(read_band(d, "B04"), off)
    nir = reflectance(read_band(d, "B08"), off)
    scl = read_band(d, "SCL")
    valid = np.isfinite(red) & np.isfinite(nir) & np.isfinite(scl) & ~np.isin(scl, SCL_INVALID)
    with np.errstate(invalid="ignore", divide="ignore"):
        ndvi = (nir - red) / (nir + red)
    valid &= np.isfinite(ndvi)
    ndvi = np.where(valid, ndvi, np.nan).astype(np.float32)
    green = valid & (ndvi > GREEN_NDVI)
    return {"year": scene["year"], "date": d, "offset": off, "ndvi": ndvi, "valid": valid,
            "green": green, "valid_fraction": float(valid.mean()),
            "green_fraction_aoi": float(green.sum() / max(valid.sum(), 1)),
            "ndvi_p50": None if not valid.any() else float(np.nanpercentile(ndvi, 50)),
            "ndvi_p99": None if not valid.any() else float(np.nanpercentile(ndvi, 99))}


def era5_dry_season(year: int) -> tuple[float, float, int]:
    js = json.loads((RAW / "open_meteo_era5_daily.json").read_text(encoding="utf-8"))["daily"]
    rain, et0 = [], []
    for t, p, e in zip(js["time"], js["precipitation_sum"], js["et0_fao_evapotranspiration"]):
        dt = date.fromisoformat(t)
        if dt.year == year and dt.month in DRY_MONTHS:
            if p is not None:
                rain.append(p)
            if e is not None:
                et0.append(e)
    return float(np.sum(rain)), float(np.mean(et0)), len(et0)


def clip01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def f_small_size(area_m2: float) -> float:
    """1 at the 2,000 m2 minimum patch, 0 at >= 10 ha, linear in log10(area) between."""
    a = min(max(area_m2, SIZE_MIN_M2), SIZE_CAP_M2)
    return clip01(1.0 - np.log10(a / SIZE_MIN_M2) / np.log10(SIZE_CAP_M2 / SIZE_MIN_M2))


def load_route_utm(to_utm: Transformer):
    fc = json.loads((OUT / "route.geojson").read_text(encoding="utf-8"))
    feat = fc["features"][0]
    return shp_transform(to_utm.transform, shape(feat["geometry"])), feat["properties"]


def make_chips(field_id: str, cx: float, cy: float, transform, years: list[dict],
               scenes: list[dict], stretch: dict, shape_hw: tuple[int, int]) -> list[str]:
    col, row = ~transform * (cx, cy)
    col, row = int(round(col)), int(round(row))
    r0, c0 = row - CHIP_HALF_PX, col - CHIP_HALF_PX
    paths = []
    for yr, sc in zip(years, scenes):
        rgb = np.full((2 * CHIP_HALF_PX, 2 * CHIP_HALF_PX, 3), 128, np.uint8)
        rr0, cc0 = max(r0, 0), max(c0, 0)
        rr1 = min(r0 + 2 * CHIP_HALF_PX, shape_hw[0])
        cc1 = min(c0 + 2 * CHIP_HALF_PX, shape_hw[1])
        win = ((rr0, rr1), (cc0, cc1))
        has_data = False
        for i, band in enumerate(("B04", "B03", "B02")):
            v = reflectance(read_band(sc["date"], band, window=win), yr["offset"])
            lo, hi = stretch[band]
            scaled = np.clip((v - lo) / (hi - lo), 0, 1) * 255
            scaled = np.where(np.isfinite(v), scaled, 128).astype(np.uint8)
            has_data |= bool(np.isfinite(v).any())
            rgb[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0, i] = scaled
        img = Image.fromarray(rgb).resize((CHIP_SIZE, CHIP_SIZE), Image.NEAREST)
        if not has_data:
            ImageDraw.Draw(img).text((8, 8), f"{yr['year']}: no data", fill=(255, 255, 255))
        elif yr["quality_flag"] != "ok":
            ImageDraw.Draw(img).text((8, 8), f"{yr['year']}: excluded (corrupt scene)",
                                     fill=(255, 255, 0))
        p = CHIPS / f"{field_id}_{yr['year']}.png"
        img.save(p)
        paths.append(p.name)
    return paths


def main() -> int:
    raw_manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    scenes = sorted(raw_manifest["s2"], key=lambda s: s["year"])
    years = [load_year(s) for s in scenes]
    by_year = {y["year"]: y for y in years}
    with rasterio.open(S2 / f"s2_{scenes[-1]['date']}_B04.tif") as src:
        transform, shape_hw = src.transform, src.shape
    with rasterio.open(RAW / "worldcover_2021.tif") as src:
        cropland = src.read(1) == WORLDCOVER_CROPLAND

    # --- scene quality: unusable years are excluded from every per-pixel test ------------
    in_crop = {y["year"]: (round(float(y["green"][cropland].mean()), 4),
                           round(float(y["green"][~cropland].mean()), 4)) for y in years}
    gf_median = float(np.median([y["green_fraction_aoi"] for y in years if y["valid"].any()]))

    def quality_flag(y: dict) -> str:
        if not y["valid"].any():
            return "no_valid_pixels: raster is all NaN; year excluded (counts as not green)"
        crop_g, other_g = in_crop[y["year"]]
        if y["green_fraction_aoi"] > ANOMALY_GREEN_RATIO * gf_median or other_g > crop_g:
            return ("radiometry_anomaly: AOI green fraction far above other years and greener "
                    "outside WorldCover cropland than inside (chip shows a corrupt, streaked "
                    "image); year EXCLUDED from all field statistics (counts as not green)")
        return "ok"

    for y in years:
        y["quality_flag"] = quality_flag(y)
        if y["quality_flag"] != "ok":
            y["valid"] = np.zeros_like(y["valid"])
            y["green"] = np.zeros_like(y["green"])
            y["ndvi"] = np.full_like(y["ndvi"], np.nan)
    excluded = [y["year"] for y in years if y["quality_flag"] != "ok"]
    for y in (*OLD_YEARS, *NEW_YEARS):
        if y in excluded:
            raise RuntimeError(f"year {y} is needed by the new-green rule but is unusable")

    # --- new-green mask -------------------------------------------------------------
    new_ok = np.logical_and.reduce([by_year[y]["green"] for y in NEW_YEARS])
    old_valid_any = np.logical_or.reduce([by_year[y]["valid"] for y in OLD_YEARS])
    old_green_any = np.logical_or.reduce([by_year[y]["green"] for y in OLD_YEARS])
    raw_mask = new_ok & old_valid_any & ~old_green_any
    opened = ndimage.binary_opening(raw_mask, structure=OPEN_STRUCT)
    labels, n_lab = ndimage.label(opened, structure=OPEN_STRUCT)
    sizes = ndimage.sum(np.ones_like(labels), labels, index=np.arange(1, n_lab + 1))
    keep_ids = [i + 1 for i, s in enumerate(sizes) if s >= MIN_PIXELS]
    keep_mask = np.isin(labels, keep_ids)
    print(f"new-green px raw={int(raw_mask.sum())} opened={int(opened.sum())} "
          f"components={n_lab} kept(>= {MIN_PIXELS} px)={len(keep_ids)}")

    # --- shared per-patch inputs ----------------------------------------------------
    crop_outside = cropland & ~keep_mask
    dist_to_crop = ndimage.distance_transform_edt(~crop_outside, sampling=PIXEL_M)
    to_utm = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    to_wgs = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    route_utm, route_props = load_route_utm(to_utm)
    latest = NEW_YEARS[-1]
    rain_mm, et0_mean, et0_days = era5_dry_season(latest)

    polys: dict[int, list] = {}
    if keep_ids:
        lab_kept = np.where(keep_mask, labels, 0).astype(np.int32)
        for geom, val in shapes(lab_kept, mask=lab_kept > 0, transform=transform, connectivity=4):
            polys.setdefault(int(val), []).append(shape(geom))
    objects = ndimage.find_objects(labels)

    cands = []
    for lid in keep_ids:
        sl = objects[lid - 1]
        pm = labels[sl] == lid
        poly_utm = unary_union(polys[lid])
        series = []
        for y in years:
            v = y["valid"][sl][pm]
            nd = y["ndvi"][sl][pm]
            nvalid = int(v.sum())
            series.append({
                "year": y["year"], "date": y["date"],
                "ndvi_mean": None if nvalid == 0 else round(float(np.nanmean(nd[v])), 4),
                "green_fraction": None if nvalid == 0 else round(float((nd[v] > GREEN_NDVI).mean()), 4),
                "valid_fraction": round(nvalid / pm.sum(), 4),
            })
        sy = {s["year"]: s for s in series}
        green_years = [s["year"] for s in series
                       if s["green_fraction"] is not None and s["green_fraction"] >= PATCH_GREEN_FRACTION]
        persistence = sum(1 for y in PERSIST_YEARS if y in green_years)
        ndvi_2017 = sy[2017]["ndvi_mean"]
        ndvi_latest = sy[latest]["ndvi_mean"]
        inc = ndvi_latest - ndvi_2017
        area = float(pm.sum() * PIXEL_M ** 2)
        iso = float(dist_to_crop[sl][pm].min())
        dist_route = float(poly_utm.distance(route_utm))
        c = poly_utm.centroid
        lon, lat = to_wgs.transform(c.x, c.y)
        f = {
            "f_proximity": clip01(1 - min(dist_route, PROX_CAP_M) / PROX_CAP_M),
            "f_isolation": clip01(min(iso, ISO_CAP_M) / ISO_CAP_M),
            "f_ndvi_increase": clip01(inc / NDVI_INC_CAP),
            "f_persistence": clip01(persistence / len(PERSIST_YEARS)),
            "f_small_size": f_small_size(area),
        }
        score = sum(WEIGHTS[k] * f[k] for k in WEIGHTS)
        cands.append({
            "lid": lid, "poly_utm": poly_utm, "cx": c.x, "cy": c.y, "series": series,
            "props": {
                "area_m2": round(area, 1),
                "centroid": [round(lon, 6), round(lat, 6)],
                "first_green_year": green_years[0] if green_years else None,
                "green_years": green_years,
                "ndvi_2017": round(ndvi_2017, 4),
                "ndvi_latest": round(ndvi_latest, 4),
                "ndvi_increase": round(inc, 4),
                "persistence_years": persistence,
                "isolation_m": round(iso, 1),
                "dist_to_route_m": round(dist_route, 1),
                "rain_dry_season_mm": round(rain_mm, 2),
                "et0_dry_season_mm": round(et0_mean, 3),
                **{k: round(v, 4) for k, v in f.items()},
                "baseline_score": round(score, 4),
            },
        })

    cands.sort(key=lambda c: c["props"]["baseline_score"], reverse=True)
    top = cands[:TOP_N]

    # --- chips: one shared stretch for every year ---------------------------------------
    CHIPS.mkdir(parents=True, exist_ok=True)
    for old in CHIPS.glob("*.png"):
        old.unlink()
    rng = np.random.default_rng(0)
    stretch = {}
    for band in ("B04", "B03", "B02"):
        pool = []
        for y, sc in zip(years, scenes):
            if not y["valid"].any():
                continue
            v = reflectance(read_band(sc["date"], band), y["offset"])[y["valid"]]
            pool.append(rng.choice(v, size=min(200_000, v.size), replace=False))
        lo, hi = np.percentile(np.concatenate(pool), STRETCH_PCT)
        stretch[band] = (float(lo), float(hi))

    features, timeseries = [], {}
    for i, c in enumerate(top, start=1):
        fid = f"KRK-F-{i:03d}"
        props = {"field_id": fid, **c["props"], "label": "Observed",
                 "label_score": "Hypothesis", "evidence_id": f"EV-S2-{i:04d}",
                 "et0_unit": "mm/day, mean over Jun-Sep", "rain_unit": "mm, total over Jun-Sep",
                 "rain_et0_year": latest, "chips": []}
        if i <= TOP_CHIPS:
            props["chips"] = make_chips(fid, c["cx"], c["cy"], transform, years, scenes,
                                        stretch, shape_hw)
        geom = shp_transform(to_wgs.transform, c["poly_utm"])
        features.append({"type": "Feature", "properties": props, "geometry": mapping(geom)})
        timeseries[fid] = c["series"]

    (OUT / "fields.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    (OUT / "field_timeseries.json").write_text(json.dumps(timeseries, indent=1), encoding="utf-8")

    manifest = {
        "generated_on": date.today().isoformat(),
        "generator": "pipeline/process_fields.py",
        "aoi_lonlat": raw_manifest["aoi_lonlat"], "crs": CRS, "pixel_m": PIXEL_M,
        "scenes": [{
            "year": y["year"], "date": y["date"], "items": s["items"],
            "processing_baseline": s["processing_baseline"], "cloud_cover": s["cloud_cover"],
            "offset_applied_dn": BOA_OFFSET_DN if y["offset"] else 0.0,
            "valid_fraction": round(y["valid_fraction"], 4),
            "green_fraction_aoi": round(y["green_fraction_aoi"], 5),
            "ndvi_p50": None if y["ndvi_p50"] is None else round(y["ndvi_p50"], 4),
            "ndvi_p99": None if y["ndvi_p99"] is None else round(y["ndvi_p99"], 4),
            "green_fraction_in_worldcover_cropland_vs_other": in_crop[y["year"]],
            "quality_flag": y["quality_flag"],
        } for y, s in zip(years, scenes)],
        "offset_rule": "reflectance = (DN - 1000)/10000 if processing_baseline >= 04.00 "
                       "(ESA BOA_ADD_OFFSET), else DN/10000",
        "scl_invalid_classes": list(SCL_INVALID),
        "thresholds": {
            "green_ndvi_gt": GREEN_NDVI,
            "green_ndvi_justification": "desert background NDVI p99 is 0.10-0.14 in every valid "
                                        "scene (scenes[].ndvi_p99), so 0.30 sits well above bare soil",
            "new_green_rule": f"green in all of {list(NEW_YEARS)} AND valid in >=1 of {list(OLD_YEARS)} "
                              f"AND not green in any valid one of {list(OLD_YEARS)}",
            "morphological_opening": "scipy.ndimage.binary_opening, 3x3 cross, 1 iteration",
            "min_component_pixels": MIN_PIXELS, "min_component_m2": SIZE_MIN_M2,
            "patch_green_fraction": PATCH_GREEN_FRACTION,
            "first_green_year": "first year the patch has >= 50% of its valid pixels green",
            "persistence_years": f"green years (same 50% rule) among {list(PERSIST_YEARS)}",
        },
        "features": {
            "isolation_m": "min distance (scipy distance_transform_edt, 10 m sampling) from the "
                           "patch to the nearest ESA WorldCover 2021 cropland (class 40) pixel "
                           "outside all candidate patches",
            "dist_to_route_m": "shapely distance polygon <-> route LineString in EPSG:32636",
            "rain_dry_season_mm": f"ERA5 precipitation_sum total, Jun-Sep {latest}, at 31.25N 36.0E",
            "et0_dry_season_mm": f"ERA5 et0_fao_evapotranspiration MEAN DAILY (mm/day), Jun-Sep "
                                 f"{latest} ({et0_days} days)",
            "ndvi_increase": f"patch mean NDVI {latest} minus patch mean NDVI 2017",
        },
        "normalisation": {
            "f_proximity": f"1 - min(dist_to_route_m, {PROX_CAP_M:.0f}) / {PROX_CAP_M:.0f}",
            "f_isolation": f"min(isolation_m, {ISO_CAP_M:.0f}) / {ISO_CAP_M:.0f}",
            "f_ndvi_increase": f"clip(ndvi_increase / {NDVI_INC_CAP}, 0, 1)",
            "f_persistence": f"persistence_years / {len(PERSIST_YEARS)}",
            "f_small_size": f"1 - log10(clip(area, {SIZE_MIN_M2:.0f}, {SIZE_CAP_M2:.0f}) / "
                            f"{SIZE_MIN_M2:.0f}) / log10({SIZE_CAP_M2:.0f} / {SIZE_MIN_M2:.0f})",
            "f_small_size_justification": "ASSUMED team prior: small plots (min patch 0.2 ha) "
                "are easier to supply from an informal tap and less likely to be a registered "
                "farm; area spans orders of magnitude, hence log scale; >= 10 ha scores 0",
            "baseline_score": " + ".join(f"{w:.2f}*{k}" for k, w in WEIGHTS.items()),
            "weights_source": "team expert prior (ASSUMED, not calibrated)",
        },
        "labels": {"measured": "Observed", "score": "Hypothesis", "route": "Simulated"},
        "counts": {
            "new_green_pixels_raw": int(raw_mask.sum()),
            "new_green_pixels_after_opening": int(opened.sum()),
            "components_after_opening": int(n_lab),
            "candidates_ge_min_size": len(cands),
            "fields_written": len(features),
            "chips_written": sum(len(f["properties"]["chips"]) for f in features),
        },
        "chips": {"fields": TOP_CHIPS, "box_m": 2 * CHIP_HALF_PX * PIXEL_M, "size_px": CHIP_SIZE,
                  "bands": "B04/B03/B02", "stretch": "global per-band percentiles "
                  f"{STRETCH_PCT} of offset-corrected reflectance, pooled over all valid years",
                  "stretch_values": stretch,
                  "no_data_or_excluded_years": excluded},
        "route": {"method": route_props.get("method"), "source": route_props.get("source"),
                  "label": route_props.get("label")},
        "licences": {**LICENCES, "route": route_props.get("source")},
        "caveats": [
            "Candidates are inspection candidates, never violations.",
            "Route is approximate (Highway 15), not surveyed pipe geometry.",
            f"Only {len(cands)} patches pass the new-green rule (fewer than TOP_N={TOP_N}); "
            "no patches were added to reach 25.",
            f"{sum(1 for c in cands if c['props']['isolation_m'] <= PIXEL_M)} of {len(cands)} "
            "patches touch WorldCover 2021 cropland (isolation_m = 10 m, one pixel): they sit "
            "inside or at the edge of established farm blocks, so f_isolation is near 0 for "
            "them. The chips show many are plots inside existing farms that were fallow in "
            "2017-2018 (crop rotation is a likely alternative explanation), not new desert farms.",
            f"Years excluded as unusable: {excluded} (see scenes[].quality_flag); field series "
            "carry null for them and persistence_years counts them as not green.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"candidates={len(cands)} written={len(features)} chips={manifest['counts']['chips_written']}")
    for f in features[:5]:
        p = f["properties"]
        print(p["field_id"], p["area_m2"], p["ndvi_increase"], p["dist_to_route_m"], p["baseline_score"],
              p["first_green_year"], p["persistence_years"], p["isolation_m"], p["centroid"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
