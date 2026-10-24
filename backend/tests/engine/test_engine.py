"""Engine tests. All values are Simulated / Hypothesis; nothing here is Field-verified."""
import json
import math

import numpy as np
import pytest
from scipy import stats

from bb.engine import energy, fusion, learning, nextbest, precompute, priority, twin, volume


def _ok(iv):
    assert iv["lo"] <= iv["mean"] <= iv["hi"], iv


# ---------- interval ordering everywhere ----------
def test_interval_ordering_all_modules():
    sim = twin.simulate_segment(5000, 0.6096, 130, 500, 25, 0.01, 7)
    lr = twin.lr_line(sim["imbalance_m3h"], sim["meter_sigma_m3h"], (3.6, 72.0))
    _ok(lr)
    _ok(twin.estimate_tap_m3h(sim["imbalance_m3h"], sim["meter_sigma_m3h"]))
    _ok(fusion.lr_field(0.8))
    p = fusion.posterior(0.05, [lr, fusion.lr_field(0.8)])
    _ok(p)
    vol = volume.field_abstraction_m3_day(20000, 6.0, (0.7, 1.1))
    _ok(vol)
    _ok(priority.expected_m3_day(p, vol))
    _ok(priority.m3_per_inspection_hour(p, vol, 1.0, 1.5))
    _ok(learning.update_on_outcome(p, "inconclusive"))
    _ok(energy.kwh_per_m3({"mean": 290, "lo": 280, "hi": 300}, {"mean": 0.675, "lo": 0.6, "hi": 0.75}))


# ---------- twin ----------
def test_twin_mass_balance_and_headloss():
    r = twin.simulate_segment(20000, 0.6096, 130, 500, 0.0, 0.01, 1)
    assert r["label"] == "Simulated"
    assert r["true_inflow_m3h"] == pytest.approx(500, rel=1e-4)
    assert r["true_outflow_m3h"] == pytest.approx(500, rel=1e-4)
    # Hazen-Williams SI (A4): hf = 10.67 L Q^1.852 / (C^1.852 D^4.87)
    q = 500 / 3600
    hf = 10.67 * 20000 * q ** 1.852 / (130 ** 1.852 * 0.6096 ** 4.87)
    assert r["pressure_drop_m"] == pytest.approx(hf, rel=0.02)
    t = twin.simulate_segment(5000, 0.6096, 130, 500, 25.0, 0.01, 1)
    assert t["true_inflow_m3h"] - t["true_outflow_m3h"] == pytest.approx(25.0, rel=1e-3)


def test_lr_line_matches_closed_form():
    obs, s, a, b = 20.0, 7.0, 3.6, 72.0
    p_tap = (stats.norm.cdf((obs - a) / s) - stats.norm.cdf((obs - b) / s)) / (b - a)
    expected = p_tap / stats.norm.pdf(obs, 0, s)
    assert twin.lr_line(obs, s, (a, b))["mean"] == pytest.approx(expected, rel=1e-4)


def test_no_tap_segment_lr_at_most_about_one():
    sigma = math.sqrt(2) * 0.01 * 500
    assert twin.lr_line(0.0, sigma, (3.6, 72.0))["mean"] < 1.0
    lrs = []
    for seed in range(40):
        r = twin.simulate_segment(5000, 0.6096, 130, 500, 0.0, 0.01, seed)
        lrs.append(twin.lr_line(r["imbalance_m3h"], r["meter_sigma_m3h"], (3.6, 72.0))["mean"])
    assert float(np.median(lrs)) < 1.0


def test_tap_estimate_never_negative():
    e = twin.estimate_tap_m3h(-10.0, 7.0)
    assert e["lo"] >= 0 and e["mean"] >= 0
    e2 = twin.estimate_tap_m3h(25.0, 7.0)
    assert e2["lo"] < 25.0 < e2["hi"]


# ---------- fusion ----------
def test_lr_field_neutral_at_half():
    assert fusion.lr_field(0.5)["mean"] == pytest.approx(1.0)
    assert fusion.lr_field(0.9)["mean"] > 1 > fusion.lr_field(0.1)["mean"]


def test_fusion_beats_either_alone():
    sim = twin.simulate_segment(5000, 0.6096, 130, 500, 25.0, 0.01, 20261024)
    lr_l = twin.lr_line(sim["imbalance_m3h"], sim["meter_sigma_m3h"], (3.6, 72.0))
    lr_f = fusion.lr_field(0.8)
    p_l = fusion.posterior(0.05, [lr_l])
    p_f = fusion.posterior(0.05, [lr_f])
    p_b = fusion.posterior(0.05, [lr_l, lr_f])
    assert p_b["mean"] > p_l["mean"] and p_b["mean"] > p_f["mean"]
    assert p_b["label"] == "Hypothesis"


def test_posterior_exact_lr_is_bayes():
    p = fusion.posterior(0.2, [{"mean": 4.0, "lo": 4.0, "hi": 4.0}])
    assert p["mean"] == pytest.approx(0.25 * 4 / (1 + 0.25 * 4))


# ---------- priority / volume ----------
def test_volume_formula():
    v = volume.field_abstraction_m3_day(10000, 5.0, (0.7, 1.1))
    assert v["lo"] == pytest.approx(35.0) and v["hi"] == pytest.approx(55.0) and v["mean"] == pytest.approx(45.0)


def test_priority_exact_inputs():
    p = {"mean": 0.5, "lo": 0.5, "hi": 0.5}
    vol = {"mean": 100.0, "lo": 100.0, "hi": 100.0}
    assert priority.expected_m3_day(p, vol)["mean"] == pytest.approx(50.0)
    assert priority.m3_per_inspection_hour(p, vol, 1.0, 1.5)["mean"] == pytest.approx(20.0)


# ---------- learning ----------
def test_learning_directions():
    p = {"mean": 0.4, "lo": 0.25, "hi": 0.55}
    down = learning.update_on_outcome(p, "no_anomaly_found")
    up1 = learning.update_on_outcome(p, "anomaly_found_leak")
    up2 = learning.update_on_outcome(p, "anomaly_found_connection")
    inc = learning.update_on_outcome(p, "inconclusive")
    assert down["after"]["mean"] < p["mean"] < up1["after"]["mean"]
    assert up2["after"]["mean"] > p["mean"]
    assert abs(inc["after"]["mean"] - p["mean"]) < 0.03
    assert (inc["after"]["hi"] - inc["after"]["lo"]) > (p["hi"] - p["lo"])
    assert down["before"] == p
    with pytest.raises(ValueError):
        learning.update_on_outcome(p, "guilty")


# ---------- next best ----------
def test_eig_max_near_half():
    ps = np.linspace(0.01, 0.99, 99)
    for sens, spec in ((0.9, 0.9), (0.85, 0.95), (0.7, 0.9)):
        g = [nextbest.expected_info_gain_bits(p, sens, spec) for p in ps]
        assert 0.3 <= ps[int(np.argmax(g))] <= 0.7
    assert nextbest.expected_info_gain_bits(0.5, 1.0, 1.0) == pytest.approx(1.0)
    assert nextbest.expected_info_gain_bits(0.0, 0.9, 0.9) == 0.0


def test_rank_measurements_shape_and_order():
    cases = [{"case_id": "KRK-T-003", "layer": 2, "p": 0.5, "travel_h": 1.0, "evidence_id": "EV-TWIN-0003"},
             {"case_id": "KRK-F-001", "layer": 1, "p": 0.05, "travel_h": 2.0, "evidence_id": "EV-S2-0001"}]
    r = nextbest.rank_measurements(cases, nextbest.CATALOGUE)
    keys = {"measurement_id", "kind", "target_id", "expected_info_gain_bits", "cost_h", "gain_per_hour"}
    assert r and all(keys <= set(x) for x in r)
    gains = [x["gain_per_hour"] for x in r]
    assert gains == sorted(gains, reverse=True)
    assert not any(x["kind"] == "flow_meter_read" and x["target_id"].startswith("KRK-F") for x in r)
    fv = next(x for x in r if x["kind"] == "field_visit" and x["target_id"] == "KRK-F-001")
    assert fv["cost_h"] == pytest.approx(3.5)


# ---------- energy ----------
def test_energy_formula():
    k = energy.kwh_per_m3({"mean": 300, "lo": 300, "hi": 300}, {"mean": 0.75, "lo": 0.75, "hi": 0.75})
    assert k["mean"] == pytest.approx(0.002725 * 300 / 0.75, rel=1e-3)
    assert k["mean"] == pytest.approx(1.09, abs=0.005)  # A4 spike: 300 m -> 1.09-1.36 kWh/m3
    k2 = energy.kwh_per_m3({"mean": 300, "lo": 300, "hi": 300}, {"mean": 0.6, "lo": 0.6, "hi": 0.6})
    assert k2["mean"] == pytest.approx(1.36, abs=0.005)
    c = energy.co2_kg({"mean": 1000, "lo": 1000, "hi": 1000})
    assert c["mean"] == pytest.approx(529.79)


# ---------- precompute ----------
def _synthetic(tmp_path):
    # ~20 km synthetic line near Qatraneh (synthetic test geometry only)
    route = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"label": "Simulated"},
             "geometry": {"type": "LineString", "coordinates": [[36.00, 31.20], [36.05, 31.25], [36.10, 31.33]]}}]}

    def field(fid, lon, lat, score):
        d = 0.001
        return {"type": "Feature", "properties": {"field_id": fid, "baseline_score": score, "area_m2": 20000,
                "centroid": [lon, lat], "evidence_id": f"EV-S2-{fid[-4:]}"},
                "geometry": {"type": "Polygon", "coordinates": [[[lon - d, lat - d], [lon + d, lat - d],
                             [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]}}
    fields = {"type": "FeatureCollection", "features": [
        field("KRK-F-0001", 36.003, 31.204, 0.40),
        field("KRK-F-0002", 36.083, 31.303, 0.85),  # strongest, near the last third of the route
    ]}
    rp, fp = tmp_path / "route.geojson", tmp_path / "fields.geojson"
    rp.write_text(json.dumps(route), encoding="utf-8")
    fp.write_text(json.dumps(fields), encoding="utf-8")
    return rp, fp


def test_precompute_synthetic(tmp_path):
    rp, fp = _synthetic(tmp_path)
    out = tmp_path / "segments.json"
    assert precompute.main(["--route", str(rp), "--fields", str(fp), "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    segs = data["segments"]
    assert len(segs) >= 3 and "assumptions" in data
    for fam in ("fusion", "priority", "volume"):
        for v in data["assumptions"][fam].values():
            assert {"value", "source", "note"} <= set(v)
    injected = [s for s in segs if s["tap_injected"]]
    assert len(injected) == 1
    for i, s in enumerate(segs):
        assert s["segment_id"] == f"KRK-T-{i + 1:03d}" and s["evidence_id"] == f"EV-TWIN-{i + 1:04d}"
        assert s["geometry"]["type"] == "LineString" and len(s["geometry"]["coordinates"]) >= 2
        assert s["label"] == "Simulated"
        _ok(s["lr_line"])
        _ok(s["tap_estimate_m3h"])
        assert s["tap_estimate_m3h"]["lo"] >= 0
        assert isinstance(s["imbalance_m3h"], float)
    fc = injected[0]
    assert fc["fusion"]["field_id"] == "KRK-F-0002"
    f = fc["fusion"]
    assert f["posterior_fused"]["mean"] > max(f["posterior_line_only"]["mean"], f["posterior_field_only"]["mean"])
    assert data["fusion_case_id"] == fc["segment_id"]


def test_precompute_missing_inputs(tmp_path, capsys):
    code = precompute.main(["--route", str(tmp_path / "nope.geojson"), "--fields", str(tmp_path / "nope2.geojson"),
                            "--out", str(tmp_path / "o.json")])
    assert code == 2 and not (tmp_path / "o.json").exists()
    assert "missing input" in capsys.readouterr().err
