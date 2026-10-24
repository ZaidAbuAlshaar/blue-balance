"""Download raw inputs for the Qatrana corridor AOI into E:\\blue-balance-data\\raw.

Download only: no processing or scoring happens here. Every file is listed in
raw/manifest.json with its source item IDs and licence note.

Sources (open, no login):
- Microsoft Planetary Computer STAC: Sentinel-2 L2A, ESA WorldCover, Copernicus DEM GLO-30
- Open-Meteo archive API: ERA5 daily rain and FAO ET0

Run:  set PYTHONUTF8=1 && python pipeline/fetch_raw.py
"""
import json
import urllib.request
from datetime import date
from pathlib import Path

import odc.stac
import planetary_computer
import pystac_client

AOI = (35.86, 31.15, 36.14, 31.32)  # lon_min, lat_min, lon_max, lat_max: Qatrana / Desert Highway corridor
AOI_CENTER = (31.25, 36.0)  # lat, lon
OUT = Path(r"E:\blue-balance-data\raw")
CRS = "EPSG:32636"  # WGS 84 / UTM zone 36N
S2_BANDS = ["B02", "B03", "B04", "B08", "SCL"]
YEARS = range(2017, 2027)
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"


def write_band(da, path):
    da.odc.write_cog(str(path), overwrite=True)


def fetch_s2(cat, manifest):
    out = OUT / "s2"
    out.mkdir(parents=True, exist_ok=True)
    for year in YEARS:
        items = list(cat.search(
            collections=["sentinel-2-l2a"], bbox=AOI,
            datetime=f"{year}-06-01/{year}-09-30",
            query={"eo:cloud_cover": {"lt": 5}},
        ).items())
        if not items:
            print(f"s2 {year}: no items")
            manifest["s2"].append({"year": year, "status": "no items"})
            continue
        by_day = {}
        for item in items:
            by_day.setdefault(item.datetime.date(), []).append(item)
        # Prefer the day with the most tiles (full AOI coverage), then the clearest, then closest to mid-August.
        day = min(by_day, key=lambda d: (
            -len(by_day[d]),
            max(i.properties["eo:cloud_cover"] for i in by_day[d]),
            abs((d - date(year, 8, 15)).days),
        ))
        day_items = by_day[day]
        ds = odc.stac.load(day_items, bands=S2_BANDS, bbox=AOI, crs=CRS, resolution=10, groupby="solar_day")
        files = []
        for band in S2_BANDS:
            path = out / f"s2_{day.isoformat()}_{band}.tif"
            write_band(ds[band].isel(time=0), path)
            files.append(path.name)
        manifest["s2"].append({
            "year": year,
            "date": day.isoformat(),
            "items": [i.id for i in day_items],
            "cloud_cover": [i.properties["eo:cloud_cover"] for i in day_items],
            "processing_baseline": sorted({str(i.properties.get("s2:processing_baseline")) for i in day_items}),
            "files": files,
        })
        print(f"s2 {year}: {day} from {len(day_items)} tile(s)")


def fetch_single(cat, manifest, key, collection, band, resolution, datetime=None):
    search = cat.search(collections=[collection], bbox=AOI, datetime=datetime)
    items = list(search.items())
    ds = odc.stac.load(items, bands=[band], bbox=AOI, crs=CRS, resolution=resolution)
    da = ds[band].isel(time=0) if "time" in ds[band].dims else ds[band]
    path = OUT / f"{key}.tif"
    write_band(da, path)
    manifest[key] = {"collection": collection, "items": [i.id for i in items], "file": path.name}
    print(f"{key}: {len(items)} item(s)")


def fetch_open_meteo(manifest):
    lat, lon = AOI_CENTER
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}&start_date=2017-01-01&end_date={date.today().isoformat()}"
        "&daily=precipitation_sum,et0_fao_evapotranspiration&timezone=Asia%2FAmman"
    )
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = json.load(resp)
    path = OUT / "open_meteo_era5_daily.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    manifest["open_meteo"] = {"url": url, "file": path.name, "days": len(data["daily"]["time"])}
    print(f"open-meteo: {len(data['daily']['time'])} days")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "aoi_lonlat": AOI,
        "crs": CRS,
        "fetched_on": date.today().isoformat(),
        "licences": {
            "sentinel-2": "Copernicus Sentinel data, free and open with attribution",
            "esa-worldcover": "CC-BY-4.0",
            "cop-dem-glo-30": "Copernicus DEM licence (text not re-checked)",
            "open-meteo": "CC BY 4.0 per Open-Meteo (terms not re-checked)",
        },
        "s2": [],
    }
    cat = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    steps = [
        ("open_meteo", lambda: fetch_open_meteo(manifest)),
        ("worldcover", lambda: fetch_single(cat, manifest, "worldcover_2021", "esa-worldcover", "map", 10, "2021")),
        ("dem", lambda: fetch_single(cat, manifest, "cop_dem_glo30", "cop-dem-glo-30", "data", 30)),
        ("s2", lambda: fetch_s2(cat, manifest)),
    ]
    for name, step in steps:
        try:
            step()
        except Exception as exc:  # keep going: one failed source must not block the others
            manifest.setdefault("errors", {})[name] = f"{type(exc).__name__}: {exc}"
            print(f"{name}: FAILED {type(exc).__name__}: {exc}")
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
