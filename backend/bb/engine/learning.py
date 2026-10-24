"""Learning from field outcomes: Bayes update of a case posterior with an ASSUMED detection model.

found:      LR = P(found | real) / P(found | not real)            = 0.85 / 0.05 = 17 (nominal)
not found:  LR = (1 - P(found | real)) / (1 - P(found | not real)) = 0.15 / 0.95 ~= 0.16
inconclusive: LR ~ lognormal with median 1 (mean almost unchanged) and 5/95 at [0.5, 2] -> interval widens.

The detection probabilities are themselves uncertain (ranges below) and are sampled. The returned
posterior is still a Hypothesis; whether the outcome RECORD is Field-verified is decided by the services
layer (only for a real crew report, never for a demo input).
"""
from __future__ import annotations

import math

import numpy as np

from ._iv import Z95, as_interval, from_samples, sample

DETECTION = {
    "p_found_given_real": {"value": 0.85, "range": [0.75, 0.95], "source": "ASSUMED",
                           "note": "Crew finds the leak/connection when one exists."},
    "p_found_given_not_real": {"value": 0.05, "range": [0.02, 0.10], "source": "ASSUMED",
                               "note": "Crew reports an anomaly where the flagged one does not exist."},
    "inconclusive_lr_90": {"value": [0.5, 2.0], "source": "ASSUMED",
                           "note": "Inconclusive visit: median LR 1, adds spread only."},
}
ASSUMPTIONS = DETECTION
OUTCOMES = ("anomaly_found_leak", "anomaly_found_connection", "no_anomaly_found", "inconclusive")
N_SAMPLES = 20000


def update_on_outcome(p: dict, outcome: str, seed: int = 0) -> dict:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    before = as_interval(p)
    rng = np.random.default_rng(seed)
    ps = np.clip(sample(before, N_SAMPLES, rng, "logit"), 1e-9, 1 - 1e-9)
    lo_r, hi_r = DETECTION["p_found_given_real"]["range"]
    lo_f, hi_f = DETECTION["p_found_given_not_real"]["range"]
    sens = rng.uniform(lo_r, hi_r, N_SAMPLES)
    fp = rng.uniform(lo_f, hi_f, N_SAMPLES)
    if outcome.startswith("anomaly_found"):
        lr = sens / fp
    elif outcome == "no_anomaly_found":
        lr = (1 - sens) / (1 - fp)
    else:
        a, b = DETECTION["inconclusive_lr_90"]["value"]
        lr = np.exp(rng.normal(0.0, (math.log(b) - math.log(a)) / (2 * Z95), N_SAMPLES))
    odds = ps / (1 - ps) * lr
    after = from_samples(odds / (1 + odds))
    out = dict(after)
    out.update({
        "before": {k: before[k] for k in ("mean", "lo", "hi")},
        "after": {k: after[k] for k in ("mean", "lo", "hi")},
        "outcome": outcome,
        "lr_applied": from_samples(lr),
        "label": "Hypothesis",
    })
    return out
