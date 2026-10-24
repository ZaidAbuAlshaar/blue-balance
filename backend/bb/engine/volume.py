"""Water abstracted by an irrigated field (Layer 1). Label: Hypothesis.

m3/day = area_m2 x ET0 [mm/day] x Kc / 1000   (FAO-56 crop evapotranspiration ETc = Kc x ET0)

This is crop consumptive use only. Real abstraction is higher (irrigation losses), so this UNDER-claims,
which is the intended direction.
"""
from __future__ import annotations

from ._iv import interval

ASSUMPTIONS = {
    "kc_range": {"value": [0.7, 1.1], "source": "ASSUMED",
                 "note": "Crop coefficient range for an unknown crop; lo/hi used as the 90% bounds, mean = midpoint."},
    "irrigation_efficiency": {"value": None, "source": "ASSUMED",
                              "note": "Not applied (efficiency = 1), so volume is a lower bound on abstraction."},
}


def field_abstraction_m3_day(area_m2: float, et0_mm_day: float,
                             kc: tuple[float, float] = tuple(ASSUMPTIONS["kc_range"]["value"])) -> dict:
    if area_m2 < 0 or et0_mm_day < 0:
        raise ValueError("area and ET0 must be >= 0")
    k_lo, k_hi = float(kc[0]), float(kc[1])
    base = float(area_m2) * float(et0_mm_day) / 1000.0
    return interval(base * (k_lo + k_hi) / 2, base * k_lo, base * k_hi, unit="m3/day",
                    kc=[k_lo, k_hi], label="Hypothesis")
