# Blue Balance · Module contracts (today's build)

These are the interfaces every module builds against. Change one only by editing this file first.

## Shared conventions
- **Interval:** `{"mean": float, "lo": float, "hi": float}` is a 90% interval with `lo ≤ mean ≤ hi`. Every displayed number is an Interval, or an exact count written `{"mean": n, "lo": n, "hi": n}`.
- **Evidence label:** exactly one of `Observed`, `Simulated`, `Hypothesis`, `Field-verified` (`bb.config.LABELS`).
- **Case IDs:**
  - `KRK-T-###` = transmission segment (Layer 2: possible tap on the main line)
  - `KRK-F-###` = irrigated-field candidate (Layer 1: possible unrecorded abstraction)
  - `KRK-L-###` = distribution (Layer 3: not built today)
- **Evidence IDs:** `EV-<kind>-<n>`, e.g. `EV-S2-0007`, `EV-TWIN-0003`, `EV-ERA5-0001`, `EV-ASSUME-0002`.
- **Paths:** use `bb.config`. Raw inputs live in `E:\blue-balance-data\raw`; processed outputs go to `data/processed/` in the repo; synthetic data goes only to `data/synthetic/`.
- **Running Python:** use the installed `python` (3.11.6) with `PYTHONUTF8=1`, from `backend/` (`conftest.py` puts `bb` on the path). No new pip installs without asking. Available: numpy 2.3.4, scipy 1.16.3, pandas 2.3.3, shapely 2.1.2, pyproj 3.7.2, rasterio 1.4.4, xarray, wntr 1.5.0, networkx 3.6.1, fastapi 0.111.0, pydantic 2.13.4, httpx 0.28.1, pytest 9.0.3, PIL.
- **Language:** code and comments in English; UI strings in Arabic (Jordanian-friendly MSA) + English.

## 1. Data (owner: DATA agent) → files in `data/processed/`
| File | Content |
|---|---|
| `route.geojson` | One LineString: the **approximate** main-line route along the Desert Highway through Qatraneh. Properties: `label: "Simulated"`, `name_en: "Approximate route"`, `name_ar: "مسار تقريبي"`, `source`. |
| `fields.geojson` | Candidate green patches (Polygons, WGS84). Properties are listed below this table. |
| `field_timeseries.json` | `{field_id: [{"year", "date", "ndvi_mean", "green_fraction"}...]}` for 2017 → 2026, from the dry-season scene of each year. |
| `chips/<field_id>_<year>.png` | True-colour 256×256 chips, used by the UI's before/after card and time slider. |
| `manifest.json` | Scene IDs, processing baselines, the offset correction applied, the thresholds used and the source licences. |

`fields.geojson` properties:
- `field_id`, `area_m2`, `centroid: [lon, lat]`
- `first_green_year`, `ndvi_2017`, `ndvi_latest`, `ndvi_increase`
- `persistence_years`: green years among the last 4
- `isolation_m`: distance to existing cropland in ESA WorldCover
- `dist_to_route_m`
- `rain_dry_season_mm`: ERA5 rain over the dry-season window
- normalised features in [0, 1]: `f_proximity`, `f_isolation`, `f_ndvi_increase`, `f_persistence`, `f_small_size`
- `baseline_score` = 0.30·proximity + 0.25·isolation + 0.20·ndvi_increase + 0.15·persistence + 0.10·small_size
- `et0_dry_season_mm`
- `label: "Observed"` for measured values; derived scores carry `label_score: "Hypothesis"`
- `evidence_id`

## 2. Engine (owner: ENGINE agent), package `bb.engine`, pure functions, no DB access
```python
# bb/engine/twin.py: WNTR model of one transmission segment (Simulated)
build_segment(length_m: float, diameter_m: float, roughness_c: float, inflow_m3h: float) -> wntr.network.WaterNetworkModel
simulate_segment(length_m, diameter_m, roughness_c, inflow_m3h, tap_m3h: float, meter_error_frac: float, seed: int) -> dict
    # -> {"inflow_m3h", "outflow_m3h", "imbalance_m3h", "pressure_drop_m", "label": "Simulated"}
lr_line(imbalance_m3h: float, meter_sigma_m3h: float, tap_prior_m3h: tuple[float, float]) -> dict
    # likelihood ratio P(obs | tap) / P(obs | no tap), Interval-shaped
estimate_tap_m3h(imbalance_m3h: float, meter_sigma_m3h: float) -> dict  # Interval

# bb/engine/fusion.py
lr_field(baseline_score: float) -> dict           # documented ASSUMED calibration, Interval-shaped
posterior(prior: float, lrs: list[dict], seed: int = 0) -> dict   # Interval; Monte Carlo over LR intervals

# bb/engine/priority.py
expected_m3_day(p: dict, volume_m3_day: dict) -> dict        # Interval
m3_per_inspection_hour(p: dict, volume_m3_day: dict, travel_h: float, inspect_h: float) -> dict   # Interval

# bb/engine/volume.py
field_abstraction_m3_day(area_m2: float, et0_mm_day: float, kc: tuple[float, float]) -> dict   # Interval (Kc ASSUMED)

# bb/engine/learning.py
update_on_outcome(p: dict, outcome: str) -> dict   # outcome in {anomaly_found_leak, anomaly_found_connection, no_anomaly_found, inconclusive}
DETECTION = {...}  # ASSUMED P(found | real), P(found | not real), documented

# bb/engine/nextbest.py
expected_info_gain_bits(p: float, sensitivity: float, specificity: float) -> float
rank_measurements(cases: list[dict], catalogue: list[dict]) -> list[dict]
    # each: {measurement_id, kind, target_id, expected_info_gain_bits, cost_h, gain_per_hour}

# bb/engine/energy.py
kwh_per_m3(lift_m: dict, pump_eff: dict) -> dict          # 0.002725 * H / eta, Interval
co2_kg(kwh: dict, grid_g_per_kwh: float = 529.79) -> dict  # Ember 2024 via OWID (A4)
```
- Every assumed constant lives in one module-level dict with a source or "ASSUMED" note.
- Tests go in `backend/tests/engine/`.
- A precompute CLI, `python -m bb.engine.precompute`, writes `data/processed/segments.json`. It splits the route into segments between assumed meters; for each segment it gives the simulated meter readings, `lr_line`, the estimated tap Interval and `evidence_id`. It injects a tap in the segment nearest the strongest field candidate, so the fusion case exists, and labels it Simulated.

## 3. Services (owner: coordinator), `bb/services.py`, used by the API and by the agent tools
```python
get_priority_queue(region_id: str, limit: int, user: dict) -> dict
query_posterior(case_id: str, user: dict) -> dict
explain_ranking(case_id: str, user: dict) -> dict
propose_next_measurement(region_id: str, limit: int, user: dict) -> dict
create_work_order_draft(case_id, task, priority, text_ar, text_en, crew_ar, user: dict) -> dict
ingest_field_result(case_id: str, outcome: str, note: str | None, user: dict) -> dict
```
- `user = {"user_id", "role"}`, with role one of `inspector`, `engineer`, `admin`.
- Each service returns `{"error": "not_permitted"}` or `{"error": "unknown_case_id"}` when appropriate.
- Every result carries `label` and `evidence_id(s)`.
- The return shapes match `eval/bakeoff/cases.py::run_tool`, which the agent was tested on.

## 4. AI (owner: AI agent), packages `bb.agent` and `bb.extract`
```python
# bb/agent/loop.py
run_agent(question: str, user: dict, services, history: list | None = None) -> dict
    # -> {"answer": str, "mode": "answer" | "refusal" | "template" | "no_evidence",
    #     "tool_calls": [{"name", "args", "result"}], "evidence_ids": [...], "checks": {...},
    #     "model": str, "timing": {...}}
    # services = an object exposing the six functions above (inject a fake in tests)
# bb/agent/numcheck.py
check_numbers(answer: str, tool_results: list[dict]) -> dict   # {"ok": bool, "unmatched": [...], "ids_unknown": [...]}
# bb/agent/refusal.py
prefilter(question: str) -> str | None   # "R1" accusation/legal, "R2" personal data, else None (fixed template texts)

# bb/extract/extractor.py
extract_report(text: str, use_llm: bool = True) -> dict
    # -> {"fields": {name: {"value", "span", "start", "end", "status": "filled" | "empty_no_evidence" | "needs_confirmation"}},
    #     "method": "llm" | "rules", "flags": [...], "model": str | None}
# bb/extract/verify.py: exact-span check, offsets
# bb/extract/guard.py: instruction-like text flag + conflicting enum cues → needs_confirmation
# bb/extract/rules.py: rule-based extractor (same output shape). It is the baseline the LLM must beat.
```
- Agent model: `bb.config.AGENT_MODEL` (`qwen3.5:4b`), using the round-2 system prompt from `eval/bakeoff/cases.py::AGENT_SYSTEM_V2`.
- Extractor model: `bb.config.EXTRACT_MODEL` (`gemma4:e4b-it-qat`).
- Ollama: `bb.config.OLLAMA_URL`, raw httpx, `think: false`, `keep_alive: -1`.
- Tests: `backend/tests/agent/`, `backend/tests/extract/`. Unit tests mock Ollama; live tests are marked `@pytest.mark.llm`.
- Evals: `eval/agent/` (12 Arabic/English items) and `eval/extract/`. The extract eval runs a **frozen held-out set of ≥25 synthetic reports**, written fresh and not the bake-off dev set, and compares the LLM with the rules baseline. All of it is labelled Simulated.
