"""Interval helpers shared by the engine (see docs/CONTRACTS.md, "Interval").

An Interval is {"mean", "lo", "hi"}: a 90% interval with lo <= mean <= hi.

Sampling convention (used when an Interval must be propagated through a formula):
- lo / hi are treated as the 5th / 95th percentiles and `mean` as the median;
- the draw is a split-normal in a transformed space, so each side keeps its own width:
  "log" for positive quantities (volumes, LRs), "logit" for probabilities, "linear" otherwise;
- a degenerate Interval (lo == hi) is a constant.
The output of a propagation is summarised again as sample mean + 5th/95th percentiles.
"""
from __future__ import annotations

import math

import numpy as np

Z95 = 1.6448536269514722  # standard-normal 95th percentile
EPS = 1e-9


def interval(mean: float, lo: float, hi: float, **extra) -> dict:
    """Build an Interval and enforce lo <= mean <= hi (clamping, never re-centring)."""
    mean, lo, hi = float(mean), float(lo), float(hi)
    lo, hi = min(lo, hi), max(lo, hi)
    lo = min(lo, mean)
    hi = max(hi, mean)
    out = {"mean": mean, "lo": lo, "hi": hi}
    out.update(extra)
    return out


def exact(x: float, **extra) -> dict:
    return interval(x, x, x, **extra)


def as_interval(x) -> dict:
    """Accept a float or an Interval dict."""
    if isinstance(x, dict):
        return interval(x["mean"], x["lo"], x["hi"])
    return exact(float(x))


def from_samples(samples: np.ndarray, **extra) -> dict:
    s = np.asarray(samples, dtype=float)
    return interval(float(np.mean(s)), float(np.percentile(s, 5)), float(np.percentile(s, 95)), **extra)


def _fwd(x, space):
    if space == "log":
        return np.log(np.maximum(x, EPS))
    if space == "logit":
        x = np.clip(x, EPS, 1 - EPS)
        return np.log(x) - np.log1p(-x)
    return np.asarray(x, dtype=float)


def _inv(y, space):
    if space == "log":
        return np.exp(y)
    if space == "logit":
        return 1.0 / (1.0 + np.exp(-y))
    return y


def sample(iv, n: int, rng: np.random.Generator, space: str = "linear") -> np.ndarray:
    """Draw n samples from an Interval under the convention in the module docstring."""
    iv = as_interval(iv)
    if math.isclose(iv["lo"], iv["hi"], rel_tol=0.0, abs_tol=1e-15):
        return np.full(n, iv["mean"])
    m, lo, hi = _fwd(np.array([iv["mean"], iv["lo"], iv["hi"]]), space)
    s_lo = max((m - lo) / Z95, 0.0)
    s_hi = max((hi - m) / Z95, 0.0)
    z = rng.standard_normal(n)
    y = np.where(z < 0, m + z * s_lo, m + z * s_hi)
    return _inv(y, space)
