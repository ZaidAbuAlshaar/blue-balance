"""Replace one year's Sentinel-2 dry-season scene with a validated alternative.

Usage:  set PYTHONUTF8=1 && python pipeline/refetch_year.py 2021 2024

Same source as pipeline/fetch_raw.py (Planetary Computer STAC, sentinel-2-l2a,
eo:cloud_cover < 5, Jun-Sep, same AOI). Differences:
  * only days where ONE solar day covers every MGRS tile of the AOI are considered;
  * duplicate reprocessings of a tile are reduced to the newest one (mixing several
    reprocessings of one tile in one mosaic is the suspected cause of the corrupt 2021 scene);
  * each candidate is loaded and VALIDATED before acceptance: no all-NaN band, valid
    fraction >= MIN_VALID, and B04 median reflectance within B04_TOLERANCE of the mean of the
    neighbouring years already in raw/manifest.json.
The rejected scene's files move to raw/s2_rejected/ and the manifest keeps a record of why.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import numpy as np
import odc.stac
import planetary_computer
import pystac_client
import rasterio

AOI = (35.86, 31.15, 36.14, 31.32)
RAW = Path(r"E:\blue-balance-data\raw")
S2 = RAW / "s2"
REJECTED = RAW / "s2_rejected"
CRS = "EPSG:32636"
S2_BANDS = ["B02", "B03", "B04", "B08", "SCL"]
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SCL_INVALID = (0, 1, 3, 8, 9, 10)
MIN_VALID = 0.98
B04_TOLERANCE = 0.15      # +/- 15 % of the neighbours' mean B04 median reflectance
MAX_CANDIDATE_DAYS = 6


def baseline_offset(baselines) -> float:
    return 1000.0 if all(int(str(b).split(".")[0]) >= 4 for b in baselines) else 0.0


def b04_median_from_files(entry: dict) -> float | None:
    with rasterio.open(S2 / f"s2_{entry['date']}_B04.tif") as src:
        a = src.read(1).astype(np.float32)
    if not np.isfinite(a).any():
        return None
    return float((np.nanmedian(a) - baseline_offset(entry["processing_baseline"])) / 10000)


def neighbour_b04(manifest: dict, year: int) -> float:
    vals = []
    for e in manifest["s2"]:
        if e["year"] in (year - 1, year + 1):
            v = b04_median_from_files(e)
            if v is not None:
                vals.append(v)
    if not vals:
        raise RuntimeError(f"no usable neighbour years for {year}")
    return float(np.mean(vals))


def newest_per_tile(items):
    by_tile = {}
    for it in sorted(items, key=lambda i: i.id):  # id ends with the processing timestamp
        by_tile[it.properties.get("s2:mgrs_tile")] = it
    return list(by_tile.values())


def candidate_days(cat, year: int):
    items = list(cat.search(collections=["sentinel-2-l2a"], bbox=AOI,
                            datetime=f"{year}-06-01/{year}-09-30",
                            query={"eo:cloud_cover": {"lt": 5}}).items())
    all_tiles = {i.properties.get("s2:mgrs_tile") for i in items}
    by_day = {}
    for it in items:
        by_day.setdefault(it.datetime.date(), []).append(it)
    days = []
    for d, its in by_day.items():
        its = newest_per_tile(its)
        if {i.properties.get("s2:mgrs_tile") for i in its} == all_tiles:
            days.append((d, its))
    days.sort(key=lambda x: (abs((x[0] - date(year, 8, 15)).days),
                             max(i.properties["eo:cloud_cover"] for i in x[1])))
    return days, sorted(all_tiles)


def validate(ds, offset: float, ref_b04: float) -> tuple[bool, dict]:
    stats = {}
    for b in S2_BANDS:
        if not np.isfinite(ds[b].values).any():
            return False, {"reason": f"band {b} is all NaN"}
    scl = ds["SCL"].values
    red = ds["B04"].values.astype(np.float32)
    valid = np.isfinite(red) & np.isfinite(scl) & ~np.isin(scl, SCL_INVALID)
    for b in ("B02", "B03", "B08"):
        valid &= np.isfinite(ds[b].values)
    stats["valid_fraction"] = round(float(valid.mean()), 4)
    stats["b04_median"] = round(float((np.median(red[valid]) - offset) / 10000), 4) if valid.any() else None
    stats["b04_neighbour_mean"] = round(ref_b04, 4)
    if stats["valid_fraction"] < MIN_VALID:
        return False, {**stats, "reason": "valid fraction too low"}
    if abs(stats["b04_median"] - ref_b04) > B04_TOLERANCE * ref_b04:
        return False, {**stats, "reason": "B04 median out of line with neighbouring years"}
    return True, stats


def refetch(year: int, cat, manifest: dict) -> None:
    old = next(e for e in manifest["s2"] if e["year"] == year)
    ref = neighbour_b04(manifest, year)
    days, tiles = candidate_days(cat, year)
    print(f"{year}: {len(days)} full-coverage day(s) over tiles {tiles}; neighbour B04 {ref:.4f}")
    tried = []
    for d, its in days[:MAX_CANDIDATE_DAYS]:
        baselines = sorted({str(i.properties.get("s2:processing_baseline")) for i in its})
        offset = baseline_offset(baselines)
        ds = odc.stac.load(its, bands=S2_BANDS, bbox=AOI, crs=CRS, resolution=10,
                           groupby="solar_day", dtype="float32").isel(time=0)
        ok, stats = validate(ds, offset, ref)
        tried.append({"date": d.isoformat(), "items": [i.id for i in its], **stats})
        print(f"  {d}: {'ACCEPT' if ok else 'reject'} {stats}")
        if not ok:
            continue
        if d.isoformat() == old["date"]:
            print("  same date as the old scene; overwriting its files")
        REJECTED.mkdir(exist_ok=True)
        for f in old.get("files", []):
            if (S2 / f).exists():
                shutil.move(str(S2 / f), str(REJECTED / f))
        files = []
        for b in S2_BANDS:
            p = S2 / f"s2_{d.isoformat()}_{b}.tif"
            ds[b].odc.write_cog(str(p), overwrite=True)
            files.append(p.name)
        manifest.setdefault("s2_rejected", []).append({
            **old, "rejected_on": date.today().isoformat(),
            "reason": "all-NaN raster" if year == 2024 else "corrupt / out-of-line radiometry",
            "moved_to": str(REJECTED)})
        new = {"year": year, "date": d.isoformat(), "items": [i.id for i in its],
               "cloud_cover": [i.properties["eo:cloud_cover"] for i in its],
               "processing_baseline": baselines, "files": files,
               "selection": "refetch_year.py: one solar day covering all tiles, newest "
                            "reprocessing per tile, validated", "validation": stats,
               "candidates_tried": tried}
        manifest["s2"] = [new if e["year"] == year else e for e in manifest["s2"]]
        (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        return
    raise RuntimeError(f"{year}: no candidate passed validation: {tried}")


def main(argv: list[str]) -> int:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    cat = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    for y in (int(a) for a in argv):
        refetch(y, cat, manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
