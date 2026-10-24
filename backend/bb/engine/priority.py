"""Inspection priority. Unit of m3_per_inspection_hour:
    m3 per day of loss stopped, per hour of inspection effort  (m3/day per inspection-hour)
i.e. if the crew spends (travel_h + inspect_h) on this case, the expected daily volume it stops is
p x volume. Ranking by this number sends inspectors first where an hour buys the most water.
Candidates are inspection priorities, never violations. Label: Hypothesis.

Interval propagation: p is sampled logit-normal and volume log-normal (split-normal around `mean`,
lo/hi = 5th/95th percentiles; see bb.engine._iv), multiplied sample-wise, summarised as mean + 5/95.
"""
from __future__ import annotations

import numpy as np

from ._iv import from_samples, sample

ASSUMPTIONS = {
    "inspect_h": {"value": 1.5, "source": "ASSUMED", "note": "On-site inspection time per case."},
    "travel_h_default": {"value": 1.0, "source": "ASSUMED",
                         "note": "Default one-way travel from Karak when no route-based travel time is supplied."},
    "n_samples": {"value": 20000, "source": "method", "note": "Monte Carlo draws."},
    "seed": {"value": 0, "source": "method", "note": "Fixed seed for reproducible intervals."},
}


def _draws(p: dict, volume_m3_day: dict, seed: int):
    n = ASSUMPTIONS["n_samples"]["value"]
    rng = np.random.default_rng(seed)
    return sample(p, n, rng, "logit") * sample(volume_m3_day, n, rng, "log")


def expected_m3_day(p: dict, volume_m3_day: dict, seed: int = 0) -> dict:
    """Expected recoverable volume, m3/day = p x volume."""
    return from_samples(_draws(p, volume_m3_day, seed), unit="m3/day", label="Hypothesis")


def m3_per_inspection_hour(p: dict, volume_m3_day: dict, travel_h: float, inspect_h: float,
                           seed: int = 0) -> dict:
    """Expected m3/day of loss stopped per inspection-hour = p x volume / (travel_h + inspect_h)."""
    hours = float(travel_h) + float(inspect_h)
    if hours <= 0:
        raise ValueError("travel_h + inspect_h must be > 0")
    return from_samples(_draws(p, volume_m3_day, seed) / hours, unit="m3/day per inspection-hour",
                        effort_h=hours, label="Hypothesis")
