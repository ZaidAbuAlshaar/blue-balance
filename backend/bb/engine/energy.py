"""Energy and CO2 embedded in lost water (A4 section on energy).

kWh/m3 = rho g H / (eta x 3.6e6) = 0.002725 x H / eta   (rho = 1000 kg/m3, g = 9.81 m/s2)
CO2 kg = kWh x grid_g_per_kWh / 1000

Interval arithmetic: the formula is monotone (up in H, down in eta), so
mean = f(H_mean, eta_mean), lo = f(H_lo, eta_hi), hi = f(H_hi, eta_lo). These are bounding values,
wider than a 90% interval. Water lost at the source (illegal well) wastes no utility pumping energy;
do not apply this to it (A4: do not double-count).
"""
from __future__ import annotations

from ._iv import as_interval, interval

KWH_PER_M3_PER_M = 1000.0 * 9.81 / 3.6e6  # = 0.002725 (A4)

ASSUMPTIONS = {
    "kwh_per_m3_per_m": {"value": KWH_PER_M3_PER_M, "source": "physics: rho g / 3.6e6 (A4)",
                         "note": "0.002725 kWh per m3 per metre of head at 100% efficiency."},
    "lift_m": {"value": {"mean": 290.0, "lo": 280.0, "hi": 300.0},
               "source": "A4: computed from GeoNames/Open-Meteo elevations, Lajjun (720 m) -> Karak (~1000 m)",
               "note": "Ground-to-ground static lift only; well lift UNVERIFIED (0 here) and friction excluded, so this under-claims."},
    "pump_eff": {"value": {"mean": 0.675, "lo": 0.60, "hi": 0.75}, "source": "ASSUMED",
                 "note": "Pump-set efficiency range (A4); needs a datasheet or published audit."},
    "grid_g_per_kwh": {"value": 529.79, "source": "Ember 2024 via Our World in Data (A4)",
                       "note": "Jordan lifecycle generation intensity, not the IFI combined-margin factor."},
}


def kwh_per_m3(lift_m: dict, pump_eff: dict) -> dict:
    h, e = as_interval(lift_m), as_interval(pump_eff)
    if e["lo"] <= 0:
        raise ValueError("efficiency must be > 0")
    f = lambda H, eta: KWH_PER_M3_PER_M * H / eta  # noqa: E731
    return interval(f(h["mean"], e["mean"]), f(h["lo"], e["hi"]), f(h["hi"], e["lo"]),
                    unit="kWh/m3", label="Simulated")


def co2_kg(kwh: dict, grid_g_per_kwh: float = 529.79) -> dict:
    k = as_interval(kwh)
    g = float(grid_g_per_kwh) / 1000.0
    return interval(k["mean"] * g, k["lo"] * g, k["hi"] * g, unit="kg CO2e", grid_g_per_kwh=float(grid_g_per_kwh),
                    label="Simulated")
