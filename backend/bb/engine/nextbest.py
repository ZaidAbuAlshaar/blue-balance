"""Next-best measurement: expected information gain (bits) per hour of effort.

EIG = H(p) - [P(+) H(p|+) + P(-) H(p|-)]  with  P(+) = p sens + (1-p)(1-spec).
All test characteristics and costs below are ASSUMED (no field data yet). Label: Hypothesis.
"""
from __future__ import annotations

import math

ASSUMPTIONS = {
    "catalogue": {"value": "CATALOGUE", "source": "ASSUMED",
                  "note": "Sensitivity, specificity and hours per measurement kind are planning guesses."},
    "travel_h_default": {"value": 1.0, "source": "ASSUMED", "note": "Used when a case has no travel_h."},
}

CATALOGUE = [
    {"kind": "flow_meter_read", "sensitivity": 0.90, "specificity": 0.95, "fixed_h": 1.0, "add_travel": False,
     "applies_to": ["KRK-T"], "priority": "Must", "source": "ASSUMED"},
    {"kind": "pressure_logger", "sensitivity": 0.70, "specificity": 0.90, "fixed_h": 1.5, "add_travel": False,
     "applies_to": ["KRK-T"], "priority": "Should", "source": "ASSUMED"},
    {"kind": "field_visit", "sensitivity": 0.85, "specificity": 0.95, "fixed_h": 1.5, "add_travel": True,
     "applies_to": ["KRK-T", "KRK-F"], "priority": "Must", "source": "ASSUMED"},
    {"kind": "soil_moisture_probe", "sensitivity": 0.60, "specificity": 0.80, "fixed_h": 0.5, "add_travel": False,
     "applies_to": ["KRK-F"], "priority": "Could", "source": "ASSUMED",
     "note": "ESP32 soil-moisture device; optional, flagged Could."},
]


def _h(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def expected_info_gain_bits(p: float, sensitivity: float, specificity: float) -> float:
    p = float(p)
    pos = p * sensitivity + (1 - p) * (1 - specificity)
    neg = 1 - pos
    h_post = 0.0
    if pos > 0:
        h_post += pos * _h(p * sensitivity / pos)
    if neg > 0:
        h_post += neg * _h(p * (1 - sensitivity) / neg)
    return max(_h(p) - h_post, 0.0)


def _p_of(case: dict) -> float:
    p = case.get("p", case.get("posterior"))
    return float(p["mean"]) if isinstance(p, dict) else float(p)


def rank_measurements(cases: list[dict], catalogue: list[dict] | None = None) -> list[dict]:
    """cases: [{"case_id", "p" (float or Interval), optional "travel_h"}]. Sorted by gain_per_hour desc."""
    catalogue = CATALOGUE if catalogue is None else catalogue
    out = []
    for case in cases:
        cid = case["case_id"]
        p = _p_of(case)
        travel = float(case.get("travel_h", ASSUMPTIONS["travel_h_default"]["value"]))
        for m in catalogue:
            prefixes = m.get("applies_to")
            if prefixes and not any(cid.startswith(px) for px in prefixes):
                continue
            cost = float(m.get("fixed_h", m.get("cost_h", 1.0))) + (travel if m.get("add_travel") else 0.0)
            eig = expected_info_gain_bits(p, m["sensitivity"], m["specificity"])
            out.append({
                "measurement_id": f"MS-{cid}-{m['kind']}",
                "kind": m["kind"],
                "target_id": cid,
                "expected_info_gain_bits": eig,
                "cost_h": cost,
                "gain_per_hour": eig / cost if cost > 0 else 0.0,
                "p": p,
                "priority": m.get("priority"),
                "evidence_id": case.get("evidence_id"),
                "label": "Hypothesis",
            })
    out.sort(key=lambda r: r["gain_per_hour"], reverse=True)
    return out
