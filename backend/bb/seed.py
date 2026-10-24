"""Build the demo database from data/processed (Observed + Simulated inputs) and the engine.

Run:  set PYTHONUTF8=1 && python -m bb.seed
"""
import hashlib
import json
import math
import secrets

from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

from bb import db
from bb.config import DB_PATH, PROCESSED, SYNTHETIC
from bb.engine import fusion, priority, volume

# Every assumed constant used to build the initial posteriors. Each one is stored as evidence (kind=assumption).
ASSUMPTIONS = {
    "prior_transmission": {"value": 0.05, "source": "ASSUMED", "note": "Base rate of an illegal tap per ~5 km main-line segment; no audited data."},
    "prior_source": {"value": 0.10, "source": "ASSUMED", "note": "Base rate that a new desert green patch is unrecorded abstraction; no licence data available."},
    "kc_range": {"value": [0.7, 1.1], "source": "ASSUMED", "note": "Crop coefficient range for irrigated plots (crop type unknown)."},
    "depot_lonlat": {"value": [35.7048, 31.1853], "source": "ASSUMED", "note": "Inspection team base taken as Karak city centre."},
    "road_factor": {"value": 1.3, "source": "ASSUMED", "note": "Road distance ÷ straight-line distance."},
    "speed_kmh": {"value": 60, "source": "ASSUMED", "note": "Average driving speed."},
    "inspect_h_field": {"value": 1.5, "source": "ASSUMED", "note": "Time on site for a field inspection."},
    "inspect_h_segment": {"value": 1.0, "source": "ASSUMED", "note": "Time to read both meters and walk the segment section."},
    "link_radius_m": {"value": 1000, "source": "ASSUMED", "note": "A field within this distance of a segment is fused into that segment's case."},
}

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32636", always_xy=True).transform


def _hash_password(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()


def _demo_users():
    """Demo accounts for the local app only. Passwords live in data/synthetic/demo_users.json."""
    path = SYNTHETIC / "demo_users.json"
    if not path.exists():
        users = [
            {"user_id": "eng_a", "display_name": "مهندس أ · Engineer A", "role": "engineer"},
            {"user_id": "eng_b", "display_name": "مهندس ب · Engineer B", "role": "engineer"},
            {"user_id": "insp_1", "display_name": "مفتش ١ · Inspector 1", "role": "inspector"},
            {"user_id": "admin_1", "display_name": "مسؤول · Admin", "role": "admin"},
        ]
        for user in users:
            user["password"] = secrets.token_urlsafe(9)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"label": "Simulated", "note": "Demo accounts for the local demo only.",
                                    "users": users}, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))["users"]


def _travel_h(lonlat):
    dx_km = _haversine_km(ASSUMPTIONS["depot_lonlat"]["value"], lonlat) * ASSUMPTIONS["road_factor"]["value"]
    return round(dx_km / ASSUMPTIONS["speed_kmh"]["value"], 2)


def _haversine_km(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _load(name):
    return json.loads((PROCESSED / name).read_text(encoding="utf-8"))


def _round_iv(iv, nd):
    return {k: round(float(iv[k]), nd) for k in ("mean", "lo", "hi")}


def seed(path=DB_PATH):
    path = type(DB_PATH)(path)
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = db.connect(path)
    db.init(con)

    for user in _demo_users():
        salt = secrets.token_hex(16)
        con.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                    (user["user_id"], user["display_name"], user["role"], salt, _hash_password(user["password"], salt)))

    assumption_ids = {}
    all_assumptions = {"seed": ASSUMPTIONS}
    for module in (fusion, priority, volume):
        all_assumptions[module.__name__.split(".")[-1]] = getattr(module, "ASSUMPTIONS", {})
    n = 0
    for module_name, table in all_assumptions.items():
        for key, spec in table.items():
            n += 1
            eid = f"EV-ASSUME-{n:04d}"
            assumption_ids[f"{module_name}.{key}"] = eid
            db.add_evidence(con, eid, "Hypothesis", "assumption", spec.get("source", "ASSUMED"),
                            {"module": module_name, "key": key, **spec})

    fields = _load("fields.geojson")["features"]
    segments = _load("segments.json")
    route = _load("route.geojson")
    db.add_evidence(con, "EV-ROUTE-0001", "Simulated", "route", route["features"][0]["properties"].get("source", ""),
                    route["features"][0]["properties"])

    field_lr = {}
    for feat in fields:
        props = feat["properties"]
        fid = props["field_id"]
        db.add_evidence(con, props["evidence_id"], "Observed", "s2_field", "Sentinel-2 L2A (Copernicus), ESA WorldCover, ERA5",
                        {k: v for k, v in props.items() if not k.startswith("label")}, method="dry-season NDVI change")
        lr = fusion.lr_field(props["baseline_score"])
        field_lr[fid] = lr
        prior = ASSUMPTIONS["prior_source"]["value"]
        p = fusion.posterior(prior, [lr])
        et0_day = props["et0_dry_season_mm"]
        vol = volume.field_abstraction_m3_day(props["area_m2"], et0_day, tuple(ASSUMPTIONS["kc_range"]["value"]))
        travel = _travel_h(props["centroid"])
        inspect = ASSUMPTIONS["inspect_h_field"]["value"]
        m3h = priority.m3_per_inspection_hour(p, vol, travel, inspect)
        signals = [{"layer": "source", "signal": "new dry-season greenness (Sentinel-2)",
                    "baseline_score": round(props["baseline_score"], 2), "lr": _round_iv(lr, 2),
                    "evidence_id": props["evidence_id"], "label": "Observed"}]
        evidence_ids = [props["evidence_id"], assumption_ids["seed.prior_source"], assumption_ids["seed.kc_range"]]
        con.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?)",
                    (fid, "source", json.dumps(feat["geometry"]), "[]", travel, inspect,
                     json.dumps(evidence_ids), json.dumps(signals, ensure_ascii=False)))
        db.add_posterior(con, fid, _round_iv(p, 4), _round_iv(vol, 2), _round_iv(m3h, 3), evidence_ids,
                         "initial: prior x LR(field)", "system")

    field_geoms = {f["properties"]["field_id"]: shp_transform(TO_UTM, shape(f["geometry"])) for f in fields}
    radius = ASSUMPTIONS["link_radius_m"]["value"]
    for seg in segments["segments"]:
        sid = seg["segment_id"]
        db.add_evidence(con, seg["evidence_id"], "Simulated", "twin_segment", "WNTR 1.5.0 / EPANET 2.2 simulation",
                        {k: v for k, v in seg.items() if k != "geometry"}, method="flow balance between meters")
        line = shp_transform(TO_UTM, shape(seg["geometry"]))
        linked = sorted((fid for fid, g in field_geoms.items() if g.distance(line) <= radius),
                        key=lambda fid: -field_lr[fid]["mean"])
        lrs = [seg["lr_line"]]
        signals = [{"layer": "transmission", "signal": "flow imbalance between segment meters (simulated)",
                    "imbalance_m3h": round(seg["imbalance_m3h"], 1), "lr": _round_iv(seg["lr_line"], 2),
                    "evidence_id": seg["evidence_id"], "label": "Simulated"}]
        evidence_ids = [seg["evidence_id"], assumption_ids["seed.prior_transmission"]]
        if linked:
            best = linked[0]
            lrs.append(field_lr[best])
            best_props = next(f["properties"] for f in fields if f["properties"]["field_id"] == best)
            signals.append({"layer": "source", "signal": f"new irrigated field {best} within {radius} m of the segment",
                            "lr": _round_iv(field_lr[best], 2), "evidence_id": best_props["evidence_id"],
                            "label": "Observed"})
            evidence_ids.append(best_props["evidence_id"])
        prior = ASSUMPTIONS["prior_transmission"]["value"]
        p = fusion.posterior(prior, lrs)
        tap = seg["tap_estimate_m3h"]
        vol = {k: max(0.0, float(tap[k])) * 24 for k in ("mean", "lo", "hi")}
        mid = line.interpolate(0.5, normalized=True)
        lon, lat = Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True).transform(mid.x, mid.y)
        travel = _travel_h((lon, lat))
        inspect = ASSUMPTIONS["inspect_h_segment"]["value"]
        m3h = priority.m3_per_inspection_hour(p, vol, travel, inspect)
        con.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?)",
                    (sid, "transmission", json.dumps(seg["geometry"]), json.dumps(linked), travel, inspect,
                     json.dumps(evidence_ids), json.dumps(signals, ensure_ascii=False)))
        reason = "initial: prior x LR(line)" + (" x LR(field) [fusion]" if linked else "")
        db.add_posterior(con, sid, _round_iv(p, 4), _round_iv(vol, 2), _round_iv(m3h, 3), evidence_ids, reason, "system")

    db.audit(con, "system", "system", "seed", str(path), {"fields": len(fields), "segments": len(segments["segments"])})
    con.commit()
    return con


if __name__ == "__main__":
    con = seed()
    n_cases = con.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    print(f"seeded {DB_PATH}: {n_cases} cases")
