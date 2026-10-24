# Blue Balance (ميزان الأزرق) · Tech Stack Checklist

Status: **stack + D1–D6 APPROVED by Zaid (2026-10-24). Downloads running. No application code written. UI waits for the design brief.** Compiled from subagent reports A1–A8 (`analysis/`). Every version below was checked on this laptop or on PyPI/npm/GitHub today by the named report. Anything not checked is marked UNVERIFIED.

## 0. Decisions (approved)

- [x] **D1 Timeline:** build for the published deadline (hacking ends 19:00, submissions close 21:00).
  - [ ] NEEDS-ZAID: ask the hosts what "time limit removed" actually means.
- [x] **D2 Name (changed in U2):** **"Blue Balance (ميزان الأزرق)"** everywhere: UI, code, repo, docs, `brand/`, slides. The fresh repo is created today with nothing reused. The earlier prototype appears only in the one-line prior-work disclosure in the submission.
  - [ ] A new Blue Balance logo is needed (design brief). The old mark was moved out of `brand/`.
- [x] **D3 Python:** use the installed Python directly today and write `requirements.txt`. A uv venv comes later.
- [x] **D4 Model (changed in U2):** picks come from the measured bake-off in `MODELS.md`: agent `qwen3.5:4b`, extractor `gemma4:e4b-it-qat` (D7 pending). Waiting for Zaid's "موافق" on MODELS.md.
- [x] **D5 Main line:** an "Approximate route" along the Desert Highway through Qatraneh. No pipe features are downloaded.
- [x] **D6 Ollama:** pin v0.40.10 as is (a 14-day-old release may lack Gemma 4 support).
- [x] **D7–D9 (MODELS.md, approved):** agent `qwen3.5:4b`, extractor `gemma4:e4b-it-qat`, round-2 prompt (now V3 = V2 + the "estimates, not confirmed losses" rule), Qwen3.5-9B skipped.
- [x] **D10 Layer 1 story (approved 2026-10-24):** present it as it really is.
  - All 14 Sentinel-2 candidates near the route are dry-season greenness **inside existing WorldCover cropland** (likely crop rotation).
  - The system flags them, the isolation feature scores 0, and they stay low in the queue. That shows it does not over-flag.
  - No wider search today.
- [x] **D11 Extractor claim (approved 2026-10-24):** keep both the Gemma LLM extractor and the rules extractor. Say **"on par in our test"**: 90.9% vs 92.3% on the 30-report held-out set, which was not blinded. Never claim the LLM is better.

**Legend**
- ✅ = already installed on this laptop (checked read-only today).
- ⬇ = needs a download or install (needs Zaid's OK).
- **TODAY** = fits the published build window (hacking ends 19:00, submissions close 21:00).
- **LATER** = after the event.

**Ground rules this stack is built around**
- The event is a 12-hour on-site hackathon. Its rules say "Pre-built projects or work completed before the event are not permitted". Confirmed via the MLH events API (A1).
  - So the stack starts from a **fresh repo today** and reuses no code, data products or assets from earlier repos.
- Open-weight AI only: no closed API anywhere in a core path.
- The whole demo runs **offline on this laptop** (RTX 4060 8 GB, 16 GB RAM). C: has about 15 GB free, so all data and models go on **E:**.
- Every number carries an evidence label (Observed / Simulated / Hypothesis / Field-verified) and an interval. This is enforced in the database, not only in the UI.

---

## 1. Runtime and environment

- [ ] **Python 3.11.6** (`D:\python.exe`) ✅, TODAY. Run directly, because every backend and geo library below is already in `D:\Lib\site-packages`. Exact versions used are frozen in `requirements.txt`.
  - LATER: a uv-managed Python venv on E:. uv 0.11.21 ✅ is installed. A uv-managed interpreter avoids the `D:\Lib\sitecustomize.py` landmine.
  - → **Decision D3**
- [ ] **Node 22.17.1 + npm 10.9.2 + pnpm 11.3.0** ✅, TODAY (A6).
- [ ] **git 2.50.1** ✅, TODAY: a fresh repo created today, author Zaid Abu Alshaar (A5).
- [ ] **Data and cache root `E:\blue-balance-data\`**, TODAY (holds the raw downloads and spike outputs).
- [ ] **No Docker today.** Docker and WSL are not installed, and installing them needs admin rights and a reboot (A5).
  - LATER: Docker Engine or Podman on Linux for the ministry story, not Docker Desktop, whose licence charges large and government organisations (A5).

## 2. Backend (API, database, auth)

- [x] **FastAPI 0.143.0 + Starlette 1.3.1 + uvicorn 0.29.0**, TODAY (changed at build time). The installed 0.111.0 crashed on `FastAPI()` against Starlette 1.3.1, so it was upgraded to the newest release ≥ 14 days old (2026-10-08).
- [ ] **pydantic 2.13.1** ✅, TODAY: every request and response, and a `Quantity` type of value + interval + label + evidence_id.
- [ ] **SQLite 3.42 (stdlib) + GeoJSON text columns** ✅, TODAY. No PostGIS and no SpatiaLite (`mod_spatialite` is not available).
  - The A5 spike proved that CHECK constraints and triggers reject each of these:
    - a bad label
    - a value outside its interval
    - edits to evidence rows
    - an approver who is also the proposer
    - a map edit with no evidence
    - a report field with no source words
  - LATER: PostgreSQL 17 + PostGIS 3.6.2 (portable zip, no admin needed).
- [ ] **shapely 2.1.2 + pyproj 3.7.2** ✅, TODAY: distance-to-line, buffers and CRS transforms.
- [ ] **rasterio 1.4.4** ✅, TODAY: renders image chips offline (PNG), with no live tiling.
- [ ] **Agent streaming via `StreamingResponse` (text/event-stream)** ✅, TODAY. FastAPI 0.111 predates native SSE, so no new dependency is needed.
- [ ] **Auth: PyJWT 2.13.0** ✅ HS256 in an HttpOnly cookie, passwords hashed with stdlib `hashlib.scrypt`. TODAY.
  - 3 roles: `inspector`, `engineer`, `admin`.
  - Two engineer demo accounts, because the approver can never be the proposer (A5, A7).
- [ ] **Append-only audit log**: a SQLite table with `BEFORE UPDATE/DELETE` abort triggers and a SHA-256 hash chain (stdlib). TODAY.
- [ ] **CLI: typer 0.24.1** ✅ (`python -m mb seed` etc.), TODAY.
- [ ] **Jobs: none.** Synchronous calls + FastAPI `BackgroundTasks`, TODAY. The live re-rank must take ≤ 5 s (A5).
- [ ] **Tests: pytest 9.0.3 + httpx 0.28.1** ✅, TODAY.

## 3. Data layer (fresh fetches today, no login)

- [ ] **STAC access: pystac-client 0.9.0 + planetary-computer 1.0.0 + odc-stac 0.5.2 + xarray** ✅, TODAY (A2).
- [ ] **Sentinel-2 L2A dry-season imagery**, TODAY. Earth Search `sentinel-2-c1-l2a` gave 139 items with cloud < 5% for Jun–Sep 2026 over the AOI (A2).
  - ⚠ Earth Search has **no summer-2017 items** there; the earliest is 2018-03-12. "2017 →" (Update 1) is only possible through Planetary Computer's reprocessed L2A (2015 →). → choose 2018 → latest, or PC for 2017.
- [ ] **ERA5 rain + ET0 via the Open-Meteo archive API**, TODAY. Tested: 0.0 mm rain, 914.9 mm ET0, Jun–Sep 2026 at the AOI (A2). Its licence terms were not re-checked today (UNVERIFIED).
- [ ] **CHIRPS v2.0 monthly** (the dry-month filter, Update 1 §3.1), TODAY. Latest month 2026-09 is reachable. Licence UNVERIFIED.
- [ ] **ESA WorldCover v200 (2021) via Planetary Computer**, CC-BY-4.0, TODAY: the isolation feature (A2).
- [ ] **Copernicus DEM GLO-30 via Planetary Computer**, TODAY: elevations. Licence text not opened (A2).
- [ ] **Main-line route = "Approximate route" proxy along the Desert Highway through Qatraneh**, TODAY (Update 1 §3.1). Labelled everywhere. → **Decision D5**
  - Source: OSM. Overpass was down today (502/504), so the fallback is a hand-traced polyline labelled Simulated (A2).
- [ ] **Karak ArcGIS service: metadata only**, TODAY. No licence is stated, and the publisher is a consultancy. Never touch layer 2 (customers) or layer 8 (parcels, name-like fields) (A2, A4).
- [ ] **Today's AOI:** Qatrana main-line box `[35.88, 31.19, 36.06, 31.28]` (A2). The pilot bbox widens to 35.33–36.22 E, 30.79–31.46 N, so it includes the Ghor al-Safi side.
- [ ] **Export CRS configurable**, TODAY. Candidates are `EPSG:28191` (Palestine 1923 / Palestine Grid, per pyproj) and `EPSG:3066` (Jordan TM). The utility's real CRS is UNVERIFIED (A2, A5).
  - Always also ship a WGS84 copy, because standard GeoJSON (RFC 7946) only allows WGS84 (A5).
- [ ] LATER: **NISAR GCOV/SME2 + GRACE-FO.** Both need an **Earthdata login (NEEDS-ZAID)**, plus `asf_search`, `earthaccess` and `h5py` ⬇ (A2). GCOV is about 1.8 GB per granule.
- [ ] LATER: **geopandas, pyogrio** ⬇, the OSM Geofabrik `.pbf`, and licensed-wells import (no public dataset found).

## 4. Physics and decision engine

- [ ] **WNTR 1.5.0** (Revised BSD; bundles EPANET 2.2) ⬇, TODAY: a twin of one transmission segment with an injected tap. Its output is a flow-imbalance + pressure-gradient signal (A4).
  - Fallback ✅: the analytic Hazen-Williams model in `spikes/A4_tap_detectability.py` (already runs).
- [ ] **Bayesian fusion: hand-written odds update in NumPy 2.3.4 / SciPy 1.16.3** ✅, TODAY. Posterior odds = prior odds × LR(line) × LR(field). Closed form, instant, and every factor can be shown in the UI (A4).
  - LATER: PyMC 6.3.2 (needs Python ≥ 3.12) or NumPyro (JAX; no GPU on native Windows, UNVERIFIED).
- [ ] **Transparent baseline score** (Update 1 weights 0.30/0.25/0.20/0.15/0.10), TODAY. Shown as *expert priors* next to a stability check over 1,000 random weightings and an equal-weights comparison (A8).
- [ ] **Priority metric**: expected m³ recoverable per inspection hour, with an interval. Next-best measurement by expected information gain. NumPy ✅, TODAY.
- [ ] **NetworkX 3.6.1** ✅, TODAY: topology and travel-cost paths.
- [ ] **Energy**: kWh/m³ = 0.002725 × lift H (m) ÷ pump efficiency η, shown as a range with configurable inputs. CO₂ factor for Jordan: 529.79 g/kWh (2024, Ember via Our World in Data, per A4). TODAY.
- [ ] LATER: **PyTorch Geometric 2.8.1** (MIT) ⬇ for the physics-informed GNN. PyTorch 2.13 + CUDA ✅ already works on the RTX 4060. No GNN claim today (A4).

## 5. Open-weight AI

- [ ] **Ollama** (MIT) ⬇, TODAY: the local LLM server. Settings:
  - `OLLAMA_MODELS=E:\ollama\models`, `OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_KEEP_ALIVE=-1`
  - `OLLAMA_CONTEXT_LENGTH=8192`, set explicitly because Ollama's docs disagree on the default (A7)
  - ⚠ The newest release, v0.40.10, is one day old (2026-10-23). → **Decision D6**
- [ ] **Agent LLM: `qwen3.5:4b`** ✅ pulled (Apache-2.0, 3.32 GB), TODAY. Bake-off round 2: 10/10 Arabic tool calls, 3/3 refusals, ~1.0 s median, 3,981 MiB peak (see `MODELS.md`).
  - Fallback: `gemma4:e4b-it-qat` with the round-2 prompt (7/10).
- [ ] **Extractor LLM: `gemma4:e4b-it-qat`** ✅ pulled (Apache-2.0, 6.15 GB), TODAY. 95.9% field accuracy, 100% span match, 4,293 MiB peak (see `MODELS.md`). → **Decision D7**
  - Fallback: `qwen3.5:4b` for both roles (84.7%).
  - Both loaded together: 7,892 / 8,188 MiB (measured). Preload both before the demo; Gemma's first load from disk took 94 s.
- [ ] **LLM client: raw httpx 0.28.1** ✅ against `/api/chat`, TODAY. Zero install; `ollama-python 0.6.3` (MIT) would be optional ⬇ (A5, A7).
- [ ] **Agent orchestration: a plain Python tool-calling loop**, TODAY. One merged Analyst + Planner agent with 6 tools, 2 of which change state (`create_work_order_draft`, `ingest_field_result`). Guardrails:
  - step cap
  - pydantic validation of arguments
  - a deterministic **number checker** that handles Arabic-Indic digits and ranges: at most 2 rewrites, then a template answer, then "no evidence"
  - 2 refusal rules (legal conclusions and accusations; personal data)
  - Rejected: smolagents CodeAgent (its own docs say it is not a sandbox). PydanticAI and LangGraph are unnecessary (A7).
- [ ] **Field-report extractor (Update 1 §3.4)**: the same Gemma model with a JSON-schema `format`, returning 10 fields. A **code check** requires each field's source words to be an exact substring of the transcript, otherwise the field is blanked. **CORE today (changed in U2).** Plus an **injection guard**: Gemma obeyed an injected line in bake-off case C10. Reports with instruction-like text are flagged, and enum fields with conflicting cues are blanked. The crew confirms every field.
  - Offline fallback: a TypeScript rule-based extractor in the browser, run through the same check.
- [ ] **Speech: faster-whisper 1.2.1** ✅ in `D:\videos\tools\whisper-venv`, model large-v3 ✅ in `D:\models\hf`. STRETCH today.
  - It runs on CPU, because the LLM and Whisper together probably exceed 8 GB VRAM (A3, A7).
  - Only large-v3 is on disk. The CPU-friendly `small`/`medium` models would be ⬇ (size UNVERIFIED).
- [ ] **Agent evals: pytest** ✅. 12 Arabic/English items today (`-m llm`) plus 40+ number-checker test strings (A7).
- [ ] **Recorded-run fallback**: recorded **today with the chosen open model**, badged "Recorded run" with reason and hash (A7).
- [ ] LATER: **Forecasting**: `amazon/chronos-bolt-small` (Apache-2.0, ~191 MB) or TimesFM 2.5 (Apache-2.0), against a linear-trend baseline. The blocker is per-site NDVI series, not the model (A3).
- [ ] LATER: **Prithvi-EO-2.0 fine-tune via TerraTorch.** There is no crop checkpoint and no Jordan labels, and the official config is doubtful on 8 GB (A3). Today, Layer 1 is the honest NDVI/dry-season change + baseline score, labelled as a baseline.
- [ ] LATER: **LightGBM 4.7.0** ✅ (installed) for the false-positive classifier.

## 6. Frontend (technical stack only; the visual design waits for Zaid's brief)

- [x] **Vite 8.3.4 + React 19 + TypeScript 5.9.3 (SPA)** ✅ installed in `web/`, TODAY (decided in U2). The build is served by FastAPI from the same origin, so there is no CORS.
- [ ] **maplibre-gl 6.15.0** (BSD-3) ⬇, TODAY. Since 6.9.0 it draws Arabic labels without the RTL plugin (A6).
- [ ] **Offline basemap: a local plain style JSON** (background + AOI/route GeoJSON), TODAY. No Esri or other online tiles.
  - LATER: `pmtiles 4.5.0` + a Protomaps Jordan extract (ODbL attribution) + self-hosted glyph PBFs.
- [ ] **Imagery**: pre-rendered Sentinel-2 dry-season PNG/WebP chips per site and year as MapLibre `image` sources, for the time slider and before/after card. TODAY.
- [ ] **Charts: @observablehq/plot 0.6.17** (ISC) ⬇, TODAY: interval bands and fan charts.
- [ ] **i18n/RTL: a hand-written `ar.ts`/`en.ts` dictionary + `<html lang dir>` switching + CSS logical properties**, TODAY.
  - Number formatting uses `Intl.NumberFormat('ar-JO-u-nu-latn')`; plain `ar-JO` gives Arabic-Indic digits (A6).
  - LATER: i18next 26.5.10 + react-i18next 17.1.7.
- [ ] **Components: none today.** Plain CSS variables and logical properties.
  - LATER: react-aria-components (Apache-2.0) or shadcn/ui with `rtl: true`.
- [ ] **State: @tanstack/react-query 5.104.5 + zustand 5.0.16** (MIT) ⬇, TODAY. React context + fetch is acceptable if time is short.
- [ ] **Fonts: self-hosted via Fontsource** ⬇, TODAY. **The family choice waits for the design brief.** No CDN at demo time.
- [ ] **Crew view: shown at 390 px on localhost.** No service worker today: a phone on `http://192.168.x.x` is not a secure context, so service workers and camera are blocked (MDN, per A6).
  - LATER: vite-plugin-pwa 2.0.0 + dexie 4.4.7 + local HTTPS.
- [ ] **Tests: vitest 5.0.5 + @playwright/test 1.64.1** ⬇, TODAY.
  - vitest: the formatter must refuse to render any number without a label and an interval.
  - Playwright: one smoke test of the demo path.
  - LATER: @axe-core/playwright (MPL-2.0, dev-only).
- [ ] **Install all npm packages once, early; no new packages after 17:30.** The npm registry dropped twice during today's checks (A6).

## 7. Security, privacy, responsible use

- [ ] Bind every service to `127.0.0.1`. No external telemetry, set via `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1` and `OLLAMA_NO_CLOUD=1` (A5).
- [ ] Use no personal data. Never download customer or parcel layers; use internal IDs only.
- [ ] Gate sensitive layers (candidate taps and wells) by role, and record every view and export in the audit log.
- [ ] Candidates are never shown as violations. The agent refuses legal conclusions.
- [ ] Synthetic data lives only in `data/synthetic/` and is labelled Simulated on screen. Typed demo entries carry the label "Simulated · demo entry", never Field-verified (A6).
- [ ] The repo holds no secrets; none are needed today.

## 8. Demo and ops

- [ ] **One command: `ops\start.ps1`.** It sets the env, seeds the SQLite DB on E:, starts uvicorn on 127.0.0.1:8000 and opens Chrome (A5).
- [ ] `/api/health`: DB, model digest, data-file presence, offline guard.
- [ ] **Offline test with Wi-Fi off** before 18:30.
- [ ] **Backup video: FFmpeg 9.0.2** ✅ screen capture (test gdigrab once; `drawtext` needs `fontfile=`) (A5).
- [ ] Playwright smoke test of the demo path (see §6).

---

## 9. Downloads and installs (approved by Zaid, 2026-10-24)

- [x] **WNTR 1.5.0** installed into the installed Python. Only `wntr` was added; numpy 2.3.4, scipy 1.16.3 and pandas 2.3.3 are unchanged.
  - [x] EPANET test run passed from the Arabic folder path and with temp files on E:.
  - [x] Landmine found: printing Arabic to the console crashes (cp1252). Every Python run must set `PYTHONUTF8=1`.
- [x] **Ollama v0.40.10, standalone zip** (1,586,229,413 bytes, official GitHub release) → `E:\ollama\bin`.
  - [x] SHA-256 `d52aea2d…d934eb` matches the release's `sha256sum.txt`.
  - [x] Extracted. `ollama serve` is running with the §5 env vars, listening on **127.0.0.1:11434 only** (checked with `Get-NetTCPConnection`).
- [x] **`gemma4:e4b-it-qat`** (6.15 GB, manifest `ee6656371218…`) → `E:\ollama\models`.
- [x] **`qwen3.5:4b`** (3.32 GB, manifest `d8b0f5e9760c…`) for the bake-off (Update 2 §3.3).
- [ ] **`qwen3.5:9b`** (6.55 GB) for the bake-off. The first pull failed; retrying.
- [x] **LLM bake-off** (`eval/bakeoff/`), rounds 1 + 2 for Gemma 4 E4B and Qwen3.5-4B; results are in `MODELS.md` (changed in U2).
  - [ ] Qwen3.5-9B: the first pull failed (connection reset on the hotspot). Retrying; D9.
- [x] **Frontend npm packages** in `web/`: a dependency list only, no code, 14-day minimum release age. Installed in 34 s. The age rule resolved these versions:
  - vite 8.3.4, @vitejs/plugin-react 6.1.2, typescript 5.9.3
  - vitest 5.0.3, @playwright/test 1.64.0, @types/react 19.3.0
  - plus react, react-dom, maplibre-gl, @observablehq/plot, @tanstack/react-query and zustand
- [ ] **Fonts:** wait for the design brief.
- [x] **Raw data for the Qatrana AOI** `[35.86, 31.15, 36.14, 31.32]` → `E:\blue-balance-data\raw\` (313 MB, `manifest.json` lists every item ID). Script: `pipeline/fetch_raw.py`.
  - [x] Sentinel-2 L2A from Planetary Computer: one clearest dry-season day per year, **2017 → 2026 (10 years)**; bands B02/B03/B04/B08/SCL at 10 m, EPSG:32636.
    - ⚠ Processing baselines differ: 02.12 for 2017–2020, 03.00 in 2021, and ≥04.00 from 2022. ESA's 04.00 change added a reflectance offset (BOA_ADD_OFFSET, +1000 DN). Confirm it per item and correct it before comparing NDVI across years.
  - [x] ESA WorldCover 2021 (2 items)
  - [x] Copernicus DEM GLO-30 (2 items)
  - [x] Open-Meteo ERA5 daily rain + ET0, 2017-01-01 → 2026-10-23 (3,583 days).
    - Fetched with curl, because Python's urllib failed with an expired SSL certificate in its own CA store. That's a landmine: Python HTTPS calls need `truststore` or an updated certifi.
  - [ ] CHIRPS monthly: **deferred.** It is 14.6 MB per global monthly file (~1.7 GB for 2017–2026). The ERA5 daily rain above covers today's dry-month filter.
- [ ] Optional: Whisper `small` model (CPU voice notes). Not started.

## 10. Build steps (each step starts only after approval; the UI waits for the design brief)

- [ ] **1. Approvals**
  - [x] stack
  - [x] D1–D6
  - [ ] design brief
- [ ] **2. Skeleton**
  - [ ] fresh git repo (author Zaid)
  - [ ] FastAPI + SQLite schema with the evidence constraints
  - [ ] Vite app shell
  - [ ] `ops\start.ps1`
- [ ] **3. Data**
  - [ ] dry-season Sentinel-2 chips, rain, WorldCover and DEM for the Qatrana AOI
  - [ ] the approximate route
- [ ] **4. Engine**
  - [ ] segment twin with an injected tap → LR(line)
  - [ ] field change → LR(field)
  - [ ] Bayesian fusion
  - [ ] m³/hour priority
  - [ ] next-best measurement
  - [ ] baseline vs posterior
- [ ] **5. AI**
  - [ ] Ollama + the merged agent (6 tools, number checker, refusals), model per `MODELS.md`
  - [ ] **text crew-report extractor:** 10 fields with verbatim source spans, empty when unsupported. CORE (changed in U2)
  - [ ] 12 evals
  - [ ] recorded run
- [ ] **6. UI**
  - [ ] the screens from the design brief
  - [ ] wired to the API
  - [ ] live re-rank after a field result
  - [ ] **text crew-report screen:** fields fill in with highlighted source words; empty fields marked "no evidence". CORE (changed in U2)
  - [ ] **thin map-edit review:** one draft feature plus one human Approve button, approver ≠ proposer (changed in U2)
- [ ] **7. Extras** (only if on time by ~17:30)
  - [ ] Whisper voice input
  - [ ] full map-edit flow (reject with reason, dual-CRS GeoJSON export)
- [ ] **8. Freeze ~18:00**
  - [ ] smoke test
  - [ ] Wi-Fi-off test
  - [ ] backup video
  - [ ] first submission
  - [ ] final submission before 21:00

Steps 3, 4, 5 and 6 run in parallel (subagents) once step 2 is done.
