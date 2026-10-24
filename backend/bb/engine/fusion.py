"""Fusion of independent evidence into one Bayesian posterior (label: Hypothesis).

posterior odds = prior odds x LR_line (Layer 2 twin, Simulated) x LR_field (Layer 1 Sentinel-2 score)

The two signals are treated as conditionally independent given "tap / no tap" (ASSUMED: a meter imbalance
and a green patch are produced by different physical processes). Candidates are inspection priorities,
never violations.
"""
from __future__ import annotations

import math

import numpy as np

from ._iv import Z95, from_samples, interval

ASSUMPTIONS = {
    "lr_field_form": {"value": "log10 LR = k x (score - 0.5)", "source": "ASSUMED",
                      "note": "UNCALIBRATED. Log-linear map from baseline_score in [0,1] to a likelihood ratio, "
                              "LR = 1 at score 0.5 (uninformative). It must be refit once field outcomes exist."},
    "lr_field_k": {"value": 2.0, "source": "ASSUMED",
                   "note": "Nominal slope: score 1.0 -> LR 10, score 0.0 -> LR 0.1."},
    "lr_field_k_range": {"value": [1.0, 3.0], "source": "ASSUMED",
                         "note": "Slope uncertainty; lo/hi of LR_field are the LRs at k = 1 and k = 3."},
    "lr_percentiles": {"value": [5, 95], "source": "method",
                       "note": "In posterior(), each LR Interval is a lognormal with lo/hi as its 5th/95th percentiles."},
    "n_samples": {"value": 20000, "source": "method", "note": "Monte Carlo draws in posterior()."},
    "prior_tap_per_segment": {"value": 0.05, "source": "ASSUMED",
                              "note": "Prior probability that a ~5 km main segment carries an unrecorded tap. No public base rate found; demo value."},
}


def lr_field(baseline_score: float) -> dict:
    """ASSUMED, UNCALIBRATED map score -> LR Interval (see ASSUMPTIONS)."""
    s = float(baseline_score)
    if not 0.0 <= s <= 1.0:
        raise ValueError("baseline_score must be in [0, 1]")
    k = ASSUMPTIONS["lr_field_k"]["value"]
    k_lo, k_hi = ASSUMPTIONS["lr_field_k_range"]["value"]
    vals = [10 ** (kk * (s - 0.5)) for kk in (k_lo, k_hi)]
    return interval(10 ** (k * (s - 0.5)), min(vals), max(vals), baseline_score=s,
                    calibration="ASSUMED log-linear, uncalibrated until field outcomes exist",
                    label="Hypothesis")


def _log_lr_samples(lr: dict, n: int, rng: np.random.Generator) -> np.ndarray:
    lo = max(float(lr["lo"]), 1e-300)
    hi = max(float(lr["hi"]), 1e-300)
    if math.isclose(lo, hi, rel_tol=1e-12):
        return np.full(n, math.log(max(float(lr["mean"]), 1e-300)))
    mu = 0.5 * (math.log(lo) + math.log(hi))
    sd = (math.log(hi) - math.log(lo)) / (2 * Z95)
    return rng.normal(mu, sd, size=n)


def posterior(prior: float, lrs: list[dict], seed: int = 0) -> dict:
    """Monte Carlo odds update. Returns Interval (mean, 5th, 95th) of P(tap | evidence). Label Hypothesis."""
    if not 0.0 < prior < 1.0:
        raise ValueError("prior must be in (0, 1)")
    n = ASSUMPTIONS["n_samples"]["value"]
    rng = np.random.default_rng(seed)
    log_odds = np.full(n, math.log(prior / (1 - prior)))
    for lr in lrs:
        log_odds = log_odds + _log_lr_samples(lr, n, rng)
    p = 1.0 / (1.0 + np.exp(-np.clip(log_odds, -700, 700)))
    return from_samples(p, prior=float(prior), n_lrs=len(lrs), n_samples=n, label="Hypothesis")
