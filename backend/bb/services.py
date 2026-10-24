"""Service layer: the only way the API and the agent's tools reach the data.
Role checks and audit logging happen here. Return shapes match the tools the agent
model was bake-off tested on (eval/bakeoff/cases.py::run_tool)."""
import json
import uuid

from pyproj import Transformer

from bb import db
from bb.config import REGION_ID
from bb.engine import learning, nextbest, priority

READ_ROLES = {"inspector", "engineer"}
DRAFT_ROLES = {"engineer"}
INGEST_ROLES = {"inspector", "engineer"}
APPROVE_ROLES = {"engineer"}
OUTCOMES = ("anomaly_found_leak", "anomaly_found_connection", "no_anomaly_found", "inconclusive")
TASKS = ("inspect_connection", "inspect_leak", "inspect_field")
PRIORITIES = ("high", "medium", "low")
EDIT_KINDS = ("new_connection", "tap_location", "undocumented_segment")
EXPORT_CRS = ("EPSG:4326", "EPSG:28191", "EPSG:3066")


def _actor_type(user):
    return "agent" if user.get("via") == "agent" else "user"


def _iv(row, prefix, ndigits):
    return {k: round(row[f"{prefix}_{k}"], ndigits) for k in ("mean", "lo", "hi")}


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"


class Services:
    def __init__(self, con):
        self.con = con

    # ---------------------------------------------------------------- helpers
    def _deny(self, user, action, target=None):
        db.audit(self.con, user.get("user_id", "?"), _actor_type(user), f"denied:{action}", target, {"role": user.get("role")})
        self.con.commit()
        return {"error": "not_permitted"}

    def _case(self, case_id):
        return self.con.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()

    def _ranked(self):
        rows = self.con.execute(
            """SELECT c.case_id, c.layer, c.travel_h, c.inspect_h, p.* FROM cases c
               JOIN posteriors p ON p.case_id = c.case_id
               WHERE p.version = (SELECT MAX(version) FROM posteriors WHERE case_id = c.case_id)
               ORDER BY p.m3h_mean DESC, c.case_id""").fetchall()
        return {row["case_id"]: (rank, row) for rank, row in enumerate(rows, start=1)}

    def _queue_item(self, rank, row):
        return {"case_id": row["case_id"], "layer": row["layer"], "rank": rank,
                "m3_per_insp_hour": _iv(row, "m3h", 1), "p": _iv(row, "p", 2),
                "volume_m3_day": _iv(row, "vol", 1), "posterior_version": row["version"],
                "label": row["label"], "evidence_id": json.loads(row["evidence_ids"])[0]}

    # ------------------------------------------------------------- agent tools
    def get_priority_queue(self, region_id, limit, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "get_priority_queue", region_id)
        if region_id != REGION_ID:
            return {"error": "unknown_region"}
        ranked = sorted(self._ranked().values(), key=lambda x: x[0])[: max(1, min(int(limit or 5), 25))]
        db.audit(self.con, user["user_id"], _actor_type(user), "view_queue", region_id, {"limit": limit})
        self.con.commit()
        return {"label": "Hypothesis", "unit": "m3 of loss per day stopped, per inspection hour",
                "queue": [self._queue_item(rank, row) for rank, row in ranked]}

    def query_posterior(self, case_id, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "query_posterior", case_id)
        ranked = self._ranked()
        if case_id not in ranked:
            return {"error": "unknown_case_id"}
        rank, row = ranked[case_id]
        db.audit(self.con, user["user_id"], _actor_type(user), "view_case", case_id, {})
        self.con.commit()
        return {"label": "Hypothesis", "case_id": case_id, "rank": rank, "p": _iv(row, "p", 2),
                "volume_m3_day": _iv(row, "vol", 1), "m3_per_insp_hour": _iv(row, "m3h", 1),
                "posterior_version": row["version"], "evidence_ids": json.loads(row["evidence_ids"])}

    def explain_ranking(self, case_id, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "explain_ranking", case_id)
        ranked = self._ranked()
        case = self._case(case_id)
        if case is None or case_id not in ranked:
            return {"error": "unknown_case_id"}
        rank, row = ranked[case_id]
        return {"label": "Hypothesis", "case_id": case_id, "rank": rank,
                "terms": {"volume_m3_day": _iv(row, "vol", 1), "probability": _iv(row, "p", 2),
                          "time_h": round(case["travel_h"] + case["inspect_h"], 1)},
                "layer_contributions": json.loads(case["signals"]),
                "linked_case_ids": json.loads(case["linked_case_ids"]),
                "reason": row["reason"]}

    def propose_next_measurement(self, region_id, limit, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "propose_next_measurement", region_id)
        cases = [{"case_id": cid, "layer": row["layer"], "p": row["p_mean"], "travel_h": row["travel_h"],
                  "evidence_id": json.loads(row["evidence_ids"])[0]}
                 for cid, (rank, row) in sorted(self._ranked().items(), key=lambda kv: kv[1][0])[:10]]
        ranked = nextbest.rank_measurements(cases, nextbest.CATALOGUE)[: max(1, min(int(limit or 3), 3))]
        evidence = {c["case_id"]: c["evidence_id"] for c in cases}
        items = [{**m, "expected_info_gain_bits": round(m["expected_info_gain_bits"], 2),
                  "cost_h": round(m["cost_h"], 1), "gain_per_hour": round(m["gain_per_hour"], 2),
                  "evidence_id": evidence.get(m["target_id"])} for m in ranked]
        return {"label": "Hypothesis", "measurements": items}

    def create_work_order_draft(self, case_id, task, priority_level, text_ar, text_en, crew_ar, user):
        if user.get("role") not in DRAFT_ROLES:
            return self._deny(user, "create_work_order_draft", case_id)
        if self._case(case_id) is None:
            return {"error": "unknown_case_id"}
        if task not in TASKS or priority_level not in PRIORITIES:
            return {"error": "invalid_arguments"}
        wo_id = _new_id("WO")
        self.con.execute(
            """INSERT INTO work_orders (wo_id, case_id, task, priority, text_ar, text_en, crew_ar, status,
               requested_by, requested_via, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (wo_id, case_id, task, priority_level, text_ar, text_en, crew_ar, "pending_approval",
             user["user_id"], "agent" if user.get("via") == "agent" else "ui", db.now()))
        db.audit(self.con, user["user_id"], _actor_type(user), "create_work_order_draft", wo_id, {"case_id": case_id})
        self.con.commit()
        return {"label": "Simulated", "wo_id": wo_id, "status": "pending_approval", "requested_by": user["user_id"],
                "note": "A different engineer must approve this draft in the Work Orders screen."}

    def ingest_field_result(self, case_id, outcome, note, user):
        if user.get("role") not in INGEST_ROLES:
            return self._deny(user, "ingest_field_result", case_id)
        case = self._case(case_id)
        if case is None:
            return {"error": "unknown_case_id"}
        if outcome not in OUTCOMES:
            return {"error": "invalid_outcome"}
        ranked_before = self._ranked()
        rank_before, before = ranked_before[case_id]
        p_before = {k: before[f"p_{k}"] for k in ("mean", "lo", "hi")}
        updated = learning.update_on_outcome(p_before, outcome)
        p_after = updated.get("after", updated)
        vol = {k: before[f"vol_{k}"] for k in ("mean", "lo", "hi")}
        m3h = priority.m3_per_inspection_hour(p_after, vol, case["travel_h"], case["inspect_h"])
        result_id = _new_id("FR")
        evidence_id = f"EV-FR-{result_id[3:]}"
        clean_note = (note or "")[:300]
        db.add_evidence(self.con, evidence_id, "Simulated", "field_result", "demo entry (no real field visit)",
                        {"case_id": case_id, "outcome": outcome, "untrusted_crew_note": clean_note})
        after_id = db.add_posterior(
            self.con, case_id, p_after, vol, m3h, json.loads(before["evidence_ids"]) + [evidence_id],
            f"Bayes update on field outcome '{outcome}'", user["user_id"])
        self.con.execute(
            """INSERT INTO field_results (result_id, case_id, outcome, note, label, submitted_by,
               posterior_before, posterior_after, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
            (result_id, case_id, outcome, clean_note, "Simulated", user["user_id"],
             before["posterior_id"], after_id, db.now()))
        db.audit(self.con, user["user_id"], _actor_type(user), "ingest_field_result", case_id, {"outcome": outcome})
        self.con.commit()
        rank_after, after = self._ranked()[case_id]
        return {"label": "Simulated", "result_id": result_id, "case_id": case_id, "outcome": outcome,
                "posterior_before": round(before["p_mean"], 2), "posterior_after": round(after["p_mean"], 2),
                "p_after": _iv(after, "p", 2), "rank_before": rank_before, "rank_after": rank_after,
                "posterior_version": after["version"], "evidence_id": evidence_id}

    # --------------------------------------------------------------- UI only
    def decide_work_order(self, wo_id, approve, user):
        """Human approval. Agents never reach this; the DB also blocks self-approval."""
        if user.get("via") == "agent" or user.get("role") not in APPROVE_ROLES:
            return self._deny(user, "decide_work_order", wo_id)
        wo = self.con.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        if wo is None:
            return {"error": "unknown_work_order"}
        if wo["requested_by"] == user["user_id"]:
            return self._deny(user, "self_approval", wo_id)
        if wo["status"] != "pending_approval":
            return {"error": "already_decided"}
        status = "approved" if approve else "rejected"
        self.con.execute("UPDATE work_orders SET status = ?, decided_by = ?, decided_at = ? WHERE wo_id = ?",
                         (status, user["user_id"], db.now(), wo_id))
        db.audit(self.con, user["user_id"], "user", f"work_order_{status}", wo_id, {})
        self.con.commit()
        return {"wo_id": wo_id, "status": status, "decided_by": user["user_id"]}

    def list_work_orders(self, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "list_work_orders")
        rows = self.con.execute("SELECT * FROM work_orders ORDER BY created_at DESC").fetchall()
        return {"work_orders": [dict(r) for r in rows]}

    def create_map_edit(self, case_id, kind, geometry, evidence_ids, user):
        if user.get("role") not in INGEST_ROLES:
            return self._deny(user, "create_map_edit", case_id)
        if self._case(case_id) is None or kind not in EDIT_KINDS or not evidence_ids:
            return {"error": "invalid_arguments"}
        edit_id = _new_id("ME")
        self.con.execute(
            """INSERT INTO map_edits (edit_id, case_id, kind, geometry, evidence_ids, status, proposed_by, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (edit_id, case_id, kind, json.dumps(geometry), json.dumps(evidence_ids), "draft", user["user_id"], db.now()))
        db.audit(self.con, user["user_id"], _actor_type(user), "create_map_edit", edit_id, {"case_id": case_id})
        self.con.commit()
        return {"edit_id": edit_id, "status": "draft", "label": "Hypothesis"}

    def decide_map_edit(self, edit_id, approve, reason, user):
        if user.get("via") == "agent" or user.get("role") not in APPROVE_ROLES:
            return self._deny(user, "decide_map_edit", edit_id)
        edit = self.con.execute("SELECT * FROM map_edits WHERE edit_id = ?", (edit_id,)).fetchone()
        if edit is None:
            return {"error": "unknown_map_edit"}
        if edit["proposed_by"] == user["user_id"]:
            return self._deny(user, "self_approval", edit_id)
        if edit["status"] != "draft":
            return {"error": "already_decided"}
        status = "approved" if approve else "rejected"
        self.con.execute("UPDATE map_edits SET status = ?, decided_by = ?, reason = ?, decided_at = ? WHERE edit_id = ?",
                         (status, user["user_id"], reason, db.now(), edit_id))
        db.audit(self.con, user["user_id"], "user", f"map_edit_{status}", edit_id, {"reason": reason})
        self.con.commit()
        return {"edit_id": edit_id, "status": status, "decided_by": user["user_id"]}

    def list_map_edits(self, user):
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "list_map_edits")
        rows = self.con.execute("SELECT * FROM map_edits ORDER BY created_at DESC").fetchall()
        return {"map_edits": [{**dict(r), "geometry": json.loads(r["geometry"]),
                               "evidence_ids": json.loads(r["evidence_ids"])} for r in rows]}

    def export_map_edit(self, edit_id, crs, user):
        """Approved edits only. Returns GeoJSON in WGS84 (RFC 7946) and, if asked, a legacy-CRS copy."""
        if user.get("role") not in APPROVE_ROLES:
            return self._deny(user, "export_map_edit", edit_id)
        if crs not in EXPORT_CRS:
            return {"error": "unsupported_crs", "supported": list(EXPORT_CRS)}
        edit = self.con.execute("SELECT * FROM map_edits WHERE edit_id = ?", (edit_id,)).fetchone()
        if edit is None or edit["status"] != "approved":
            return {"error": "not_approved"}
        geometry = json.loads(edit["geometry"])
        props = {"edit_id": edit_id, "case_id": edit["case_id"], "kind": edit["kind"],
                 "evidence_ids": json.loads(edit["evidence_ids"]), "proposed_by": edit["proposed_by"],
                 "approved_by": edit["decided_by"], "approved_at": edit["decided_at"], "label": "Hypothesis"}
        out = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": geometry, "properties": props}]}
        if crs != "EPSG:4326":
            transform = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
            out["crs"] = {"type": "name", "properties": {"name": crs}}
            out["features"][0]["geometry"] = _transform_geometry(geometry, transform)
        db.audit(self.con, user["user_id"], "user", "export_map_edit", edit_id, {"crs": crs})
        self.con.commit()
        return out

    def map_layers(self, user):
        """Case geometries are sensitive: only inspectors and engineers see them, and every view is logged."""
        if user.get("role") not in READ_ROLES:
            return self._deny(user, "view_sensitive_layers")
        ranked = self._ranked()
        features = []
        for row in self.con.execute("SELECT * FROM cases"):
            rank, post = ranked[row["case_id"]]
            features.append({"type": "Feature", "geometry": json.loads(row["geometry"]),
                             "properties": {"case_id": row["case_id"], "layer": row["layer"], "rank": rank,
                                            "p_mean": round(post["p_mean"], 2), "label": "Hypothesis",
                                            "linked_case_ids": json.loads(row["linked_case_ids"])}})
        db.audit(self.con, user["user_id"], _actor_type(user), "view_sensitive_layers", None, {"count": len(features)})
        self.con.commit()
        return {"type": "FeatureCollection", "features": features}

    def audit_log(self, user):
        if user.get("role") != "admin":
            return self._deny(user, "view_audit_log")
        rows = self.con.execute("SELECT * FROM audit_log ORDER BY seq DESC LIMIT 200").fetchall()
        return {"chain": db.verify_audit_chain(self.con), "rows": [dict(r) for r in rows]}

    def transparency(self):
        counts = {r["label"]: r["n"] for r in self.con.execute("SELECT label, COUNT(*) AS n FROM evidence GROUP BY label")}
        assumptions = [json.loads(r["payload"]) | {"evidence_id": r["evidence_id"]}
                       for r in self.con.execute("SELECT * FROM evidence WHERE kind = 'assumption'")]
        return {"evidence_by_label": counts, "assumptions": assumptions,
                "field_verified_count": counts.get("Field-verified", 0)}


def _transform_geometry(geometry, transform):
    def walk(coords):
        if isinstance(coords[0], (int, float)):
            return list(transform(coords[0], coords[1]))
        return [walk(c) for c in coords]
    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}


# ------------------------------------------------------------ demo views
def _bounded_product(a, b):
    """Bounding interval of a product of two non-negative intervals."""
    return {"mean": a["mean"] * b["mean"], "lo": a["lo"] * b["lo"], "hi": a["hi"] * b["hi"]}


def fusion_breakdown(svc, case_id, user):
    """Initial fusion (before any field result): posterior from each signal alone and from both."""
    from bb.engine import fusion
    from bb.seed import ASSUMPTIONS as SEED_ASSUMPTIONS
    if user.get("role") not in READ_ROLES:
        return svc._deny(user, "fusion_breakdown", case_id)
    case = svc._case(case_id)
    if case is None:
        return {"error": "unknown_case_id"}
    signals = json.loads(case["signals"])
    prior = SEED_ASSUMPTIONS["prior_transmission" if case["layer"] == "transmission" else "prior_source"]["value"]
    line = [s["lr"] for s in signals if s["layer"] == "transmission"]
    field = [s["lr"] for s in signals if s["layer"] == "source"]
    out = {"case_id": case_id, "layer": case["layer"], "prior": prior, "signals": signals, "label": "Hypothesis",
           "note": "Initial fusion before any field result; LRs are uncalibrated until real outcomes exist."}
    rnd = lambda iv: {k: round(float(iv[k]), 2) for k in ("mean", "lo", "hi")}
    out["posterior_line_only"] = rnd(fusion.posterior(prior, line)) if line else None
    out["posterior_field_only"] = rnd(fusion.posterior(prior, field)) if field else None
    out["posterior_fused"] = rnd(fusion.posterior(prior, line + field)) if line and field else None
    return out


def impact(svc, user, top_n=5):
    """Expected (not verified) m3/day stoppable at the top-N cases, and the pumping energy it represents."""
    from bb.engine import energy
    if user.get("role") not in READ_ROLES:
        return svc._deny(user, "impact")
    ranked = sorted(svc._ranked().values(), key=lambda x: x[0])[:top_n]
    total = {"mean": 0.0, "lo": 0.0, "hi": 0.0}
    for _, row in ranked:
        exp = priority.expected_m3_day({k: row[f"p_{k}"] for k in ("mean", "lo", "hi")},
                                       {k: row[f"vol_{k}"] for k in ("mean", "lo", "hi")})
        for k in total:
            total[k] += float(exp[k])
    kwh_m3 = energy.kwh_per_m3(energy.ASSUMPTIONS["lift_m"]["value"], energy.ASSUMPTIONS["pump_eff"]["value"])
    kwh_day = _bounded_product(total, kwh_m3)
    co2 = energy.co2_kg(kwh_day)
    rnd = lambda iv, nd=1: {k: round(float(iv[k]), nd) for k in ("mean", "lo", "hi")}
    return {"label": "Hypothesis", "top_n": len(ranked),
            "expected_m3_day": rnd(total), "kwh_per_m3": rnd(kwh_m3, 3), "kwh_day": rnd(kwh_day), "co2_kg_day": rnd(co2),
            "assumptions": {k: energy.ASSUMPTIONS[k] for k in ("lift_m", "pump_eff", "grid_g_per_kwh")},
            "note": "Expected loss at ranked candidates, not verified recoveries. No field-verified result exists."}
