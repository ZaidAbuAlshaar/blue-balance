"""Contract checks for the DATA outputs in data/processed/ (CONTRACTS.md section 1)."""
import json
from pathlib import Path

import pytest

PROCESSED = Path(__file__).resolve().parents[3] / "data" / "processed"
YEARS = list(range(2017, 2027))
TOP_CHIPS = 10
FIELD_PROPS = {
    "field_id", "area_m2", "centroid", "first_green_year", "ndvi_2017", "ndvi_latest",
    "ndvi_increase", "persistence_years", "isolation_m", "dist_to_route_m",
    "rain_dry_season_mm", "f_proximity", "f_isolation", "f_ndvi_increase", "f_persistence",
    "f_small_size", "baseline_score", "et0_dry_season_mm", "label", "label_score", "evidence_id",
}
WEIGHTS = {"f_proximity": 0.30, "f_isolation": 0.25, "f_ndvi_increase": 0.20,
           "f_persistence": 0.15, "f_small_size": 0.10}


def load(name):
    return json.loads((PROCESSED / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fields():
    return load("fields.geojson")["features"]


@pytest.mark.parametrize("name", ["route.geojson", "fields.geojson", "field_timeseries.json",
                                  "manifest.json"])
def test_files_exist(name):
    assert (PROCESSED / name).is_file()


def test_route_contract():
    fc = load("route.geojson")
    assert len(fc["features"]) == 1
    f = fc["features"][0]
    assert f["geometry"]["type"] == "LineString"
    assert len(f["geometry"]["coordinates"]) >= 2
    p = f["properties"]
    assert p["label"] == "Simulated"
    assert p["name_en"] == "Approximate route"
    assert p["name_ar"] == "مسار تقريبي"
    assert p["source"]


def test_fields_have_contract_props(fields):
    assert fields, "no candidate fields written"
    for f in fields:
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
        missing = FIELD_PROPS - set(f["properties"])
        assert not missing, (f["properties"].get("field_id"), missing)
        p = f["properties"]
        assert p["label"] == "Observed"
        assert p["label_score"] == "Hypothesis"
        assert p["evidence_id"].startswith("EV-S2-")
        assert len(p["centroid"]) == 2


def test_scores_and_features_in_unit_interval(fields):
    for f in fields:
        p = f["properties"]
        assert 0.0 <= p["baseline_score"] <= 1.0
        for k, w in WEIGHTS.items():
            assert 0.0 <= p[k] <= 1.0, (p["field_id"], k)
        assert sum(w * p[k] for k, w in WEIGHTS.items()) == pytest.approx(p["baseline_score"], abs=1e-3)


def test_sorted_by_score_and_ids_unique(fields):
    ids = [f["properties"]["field_id"] for f in fields]
    evs = [f["properties"]["evidence_id"] for f in fields]
    assert len(set(ids)) == len(ids)
    assert len(set(evs)) == len(evs)
    assert ids == [f"KRK-F-{i:03d}" for i in range(1, len(ids) + 1)]
    scores = [f["properties"]["baseline_score"] for f in fields]
    assert scores == sorted(scores, reverse=True)
    assert len(fields) <= 25


def test_timeseries_covers_every_field_and_year(fields):
    ts = load("field_timeseries.json")
    for f in fields:
        series = ts[f["properties"]["field_id"]]
        assert [s["year"] for s in series] == YEARS
        for s in series:
            assert {"year", "date", "ndvi_mean", "green_fraction"} <= set(s)


def test_chips_exist_for_top_fields(fields):
    for f in fields[:TOP_CHIPS]:
        for y in YEARS:
            assert (PROCESSED / "chips" / f"{f['properties']['field_id']}_{y}.png").is_file()


def test_manifest_records_offset_and_licences():
    m = load("manifest.json")
    assert "offset_rule" in m
    for s in m["scenes"]:
        post = all(int(b.split(".")[0]) >= 4 for b in s["processing_baseline"])
        assert s["offset_applied_dn"] == (1000.0 if post else 0.0)
    assert {"sentinel-2", "esa-worldcover", "era5-open-meteo", "route"} <= set(m["licences"])
    assert m["counts"]["fields_written"] == len(load("fields.geojson")["features"])
