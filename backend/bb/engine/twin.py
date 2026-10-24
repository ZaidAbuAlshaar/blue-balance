"""Layer 2 hydraulic twin of ONE transmission-main segment (WNTR / EPANET 2.2). Everything here is Simulated.

Topology:  Reservoir R --P_in (L/2)--> J_mid [tap demand] --P_out (L/2)--> J_end [outflow demand]
Inflow is fixed (pumped main): J_end draws inflow - tap, so the upstream meter sees `inflow_m3h` and the
downstream meter sees `inflow_m3h - tap_m3h`. Per A4 ("TODAY SLICE"): on a main line the flow balance
between the two end meters is the tap signal; pressure is weak.

Meter model: reading = true flow x (1 + N(0, meter_error_frac)), seeded.
Imbalance noise: sigma_r = sqrt(sigma_in^2 + sigma_out^2) with sigma = meter_error_frac x Q (A4 formula),
for ONE instantaneous sample. Averaging n samples would divide by sqrt(n) but meter BIAS does not average
away (A4), so the engine deliberately uses the single-sample sigma.
"""
from __future__ import annotations

import math
import shutil
import tempfile
import uuid
from pathlib import Path

import numpy as np
from scipy import stats

from bb import config

from ._iv import interval

M3H_PER_M3S = 3600.0

ASSUMPTIONS = {
    "diameter_m": {"value": 0.6096, "source": "ASSUMED",
                   "note": "24-inch main; class 24DI Observed in ArcGIS layer 6 CAD names, inner diameter ASSUMED (A4)."},
    "roughness_c": {"value": 130.0, "source": "EPANET 2.2 manual Table 3.2 (cast iron, new, 130-140)",
                    "note": "Ductile iron ASSUMED similar to new cast iron (A4). Sensitivity case C=110 ASSUMED aged."},
    "inflow_m3h": {"value": 500.0, "source": "ASSUMED",
                   "note": "~139 L/s = 12,000 m3/day from a 2014 Jordan Times report (Qatraneh wells -> Karak) that was NOT opened today (UNVERIFIED); order of magnitude only (A4)."},
    "meter_error_frac": {"value": 0.01, "source": "ASSUMED",
                         "note": "Flow-meter 1-sigma error 1% of reading (A4 grid 0.5/1/2%). 1% meters flag taps of ~6 L/s at 3 sigma per sample (A4 spike)."},
    "tap_prior_m3h": {"value": [3.6, 72.0], "source": "ASSUMED",
                      "note": "Tap size under 'tap' hypothesis uniform over 1-20 L/s (A4 tap-size grid 1,2,5,10,20 L/s)."},
    "sigma_factor_range": {"value": [0.8, 1.25], "source": "ASSUMED",
                           "note": "The meter sigma itself is uncertain; lr_line is evaluated over sigma x [0.8, 1.25] and lo/hi are the min/max LR."},
    "reservoir_head_m": {"value": 60.0, "source": "ASSUMED",
                         "note": "Fixed upstream head only to keep pressures positive; flat segment (elevation 0) so flow, not lift, dominates (A4 Desert Highway proxy is fairly flat)."},
    "grid_points": {"value": 2001, "source": "method",
                    "note": "Numerical integration grid over the tap-size prior (trapezoid rule)."},
}

SIGMA_FACTORS = (0.8, 0.9, 1.0, 1.1, 1.25)


def _tmp_root() -> Path:
    root = config.DATA_ROOT / "tmp"
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except OSError:  # E: not mounted (e.g. CI) -> system temp
        return Path(tempfile.gettempdir())


def build_segment(length_m: float, diameter_m: float, roughness_c: float, inflow_m3h: float,
                  tap_m3h: float = 0.0):
    """WNTR model: reservoir -> pipe -> mid junction (tap) -> pipe -> end junction (outflow).

    `tap_m3h` is an optional extra keyword (default 0) so the same builder serves simulate_segment.
    """
    import wntr

    if tap_m3h < 0 or tap_m3h > inflow_m3h:
        raise ValueError("tap_m3h must be in [0, inflow_m3h]")
    wn = wntr.network.WaterNetworkModel()
    wn.options.hydraulic.headloss = "H-W"
    wn.options.hydraulic.demand_model = "DD"
    wn.options.time.duration = 0
    wn.add_reservoir("R", base_head=ASSUMPTIONS["reservoir_head_m"]["value"], coordinates=(0.0, 0.0))
    wn.add_junction("J_mid", base_demand=tap_m3h / M3H_PER_M3S, elevation=0.0, coordinates=(length_m / 2, 0.0))
    wn.add_junction("J_end", base_demand=(inflow_m3h - tap_m3h) / M3H_PER_M3S, elevation=0.0,
                    coordinates=(length_m, 0.0))
    for name, a, b in (("P_in", "R", "J_mid"), ("P_out", "J_mid", "J_end")):
        wn.add_pipe(name, a, b, length=length_m / 2, diameter=diameter_m, roughness=roughness_c, minor_loss=0.0)
    return wn


def simulate_segment(length_m, diameter_m, roughness_c, inflow_m3h, tap_m3h: float,
                     meter_error_frac: float, seed: int) -> dict:
    """Run EPANET once (steady state) and return noisy end-meter readings. Label: Simulated."""
    import wntr

    wn = build_segment(length_m, diameter_m, roughness_c, inflow_m3h, tap_m3h)
    workdir = _tmp_root() / f"bb_twin_{uuid.uuid4().hex[:10]}"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        res = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=str(workdir / "seg"))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    q_in = float(res.link["flowrate"].iloc[0]["P_in"]) * M3H_PER_M3S
    q_out = float(res.link["flowrate"].iloc[0]["P_out"]) * M3H_PER_M3S
    head_mid = float(res.node["head"].iloc[0]["J_mid"])
    head_end = float(res.node["head"].iloc[0]["J_end"])
    head_res = ASSUMPTIONS["reservoir_head_m"]["value"]

    rng = np.random.default_rng(seed)
    e_in, e_out = rng.normal(0.0, meter_error_frac, size=2)
    meas_in = q_in * (1.0 + e_in)
    meas_out = q_out * (1.0 + e_out)
    sigma = meter_error_frac * math.sqrt(meas_in ** 2 + meas_out ** 2)
    return {
        "inflow_m3h": float(meas_in),
        "outflow_m3h": float(meas_out),
        "imbalance_m3h": float(meas_in - meas_out),
        "pressure_drop_m": head_res - head_end,
        "meter_sigma_m3h": float(sigma),
        "true_inflow_m3h": q_in,
        "true_outflow_m3h": q_out,
        "true_tap_m3h": float(tap_m3h),
        "head_mid_m": head_mid,
        "head_end_m": head_end,
        "velocity_m_s": (q_in / M3H_PER_M3S) / (math.pi * diameter_m ** 2 / 4),
        "seed": int(seed),
        "meter_error_frac": float(meter_error_frac),
        "solver": f"WNTR {wntr.__version__} EpanetSimulator (EPANET 2.2)",
        "label": "Simulated",
    }


def _log_lr(obs: float, sigma: float, a: float, b: float, n_grid: int) -> float:
    """log [ p(obs | tap ~ U(a,b), noise N(0,sigma)) / p(obs | no tap) ], numerically on a grid."""
    t = np.linspace(a, b, n_grid)
    logpdf = stats.norm.logpdf(obs, loc=t, scale=sigma)
    mx = float(np.max(logpdf))
    integral = np.trapezoid(np.exp(logpdf - mx), t) / (b - a)
    log_p_tap = mx + math.log(max(integral, 1e-300))
    log_p_none = float(stats.norm.logpdf(obs, loc=0.0, scale=sigma))
    return log_p_tap - log_p_none


def lr_line(imbalance_m3h: float, meter_sigma_m3h: float,
            tap_prior_m3h: tuple[float, float] = tuple(ASSUMPTIONS["tap_prior_m3h"]["value"])) -> dict:
    """Likelihood ratio P(obs | tap) / P(obs | no tap) as an Interval.

    - tap: tap size uniform over tap_prior_m3h, convolved with Gaussian meter noise (grid integral);
    - no tap: imbalance ~ N(0, sigma).
    Uncertainty: sigma itself is ASSUMED uncertain by x[0.8, 1.25]; mean = LR at the nominal sigma,
    lo/hi = min/max LR over the sigma range. This is a sensitivity band, not a sampled 90% interval.
    """
    a, b = float(tap_prior_m3h[0]), float(tap_prior_m3h[1])
    if not (b > a >= 0) or meter_sigma_m3h <= 0:
        raise ValueError("need 0 <= a < b and sigma > 0")
    n = ASSUMPTIONS["grid_points"]["value"]
    logs = {f: _log_lr(imbalance_m3h, meter_sigma_m3h * f, a, b, n) for f in SIGMA_FACTORS}
    vals = [math.exp(min(v, 700.0)) for v in logs.values()]
    return interval(math.exp(min(logs[1.0], 700.0)), min(vals), max(vals),
                    log10_mean=logs[1.0] / math.log(10),
                    sigma_m3h=float(meter_sigma_m3h), tap_prior_m3h=[a, b],
                    method="grid-integrated uniform tap prior x Gaussian meter noise; sigma x [0.8, 1.25]",
                    label="Simulated")


def estimate_tap_m3h(imbalance_m3h: float, meter_sigma_m3h: float) -> dict:
    """Tap size Interval: flat prior on tap >= 0, Gaussian noise -> normal truncated at 0 (mean, 5th, 95th)."""
    if meter_sigma_m3h <= 0:
        raise ValueError("sigma > 0")
    alpha = (0.0 - imbalance_m3h) / meter_sigma_m3h
    dist = stats.truncnorm(alpha, np.inf, loc=imbalance_m3h, scale=meter_sigma_m3h)
    return interval(float(dist.mean()), float(dist.ppf(0.05)), float(dist.ppf(0.95)),
                    unit="m3/h", method="flat prior on [0, inf), truncated normal", label="Simulated")
