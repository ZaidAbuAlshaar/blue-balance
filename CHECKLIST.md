# Blue Balance (ميزان الأزرق) · CHECKLIST

> **This file is the long-term roadmap.** Today's plan for Hacktoberfest Hack Day Amman x JOSA (2026-10-24) is the 8 build steps in [TECH_STACK.md §10](TECH_STACK.md). Tasks that belong to those 8 steps carry **[TODAY]** in their Task line. Everything else is post-event.

Compiled on 2026-10-24 from the brief, Update 1, Update 2, TECH_STACK.md and analyst reports A1–A8 (`analysis/`). Nothing is ticked yet. Hacking ends at 19:00, submissions close at 21:00, and pre-built work is banned.

**Tags**
- **[TODAY]**: part of TECH_STACK.md §10, build steps 1–8.
- **[U1]**: new in Update 1.
- **(changed in U2)**: changed by Update 2 §1 (final decisions).
- **Effort** uses the A1 scale: S ≤ 30 min, M ≤ 1.5 h, L ≤ 3 h, XL > 3 h. For post-event tasks, read it as relative size.
- **Owner** stays TBD in every task. The proposal is under *Team split proposal*.

**Fixed decisions this roadmap reflects**
- Name: **Blue Balance (ميزان الأزرق)**. (changed in U2)
- Frontend: Vite + React + TypeScript + MapLibre. (changed in U2)
- Backend: FastAPI + SQLite + GeoJSON today; PostgreSQL + PostGIS later. No Docker today.
- Agent and extractor LLM: per MODELS.md (bake-off run 2026-10-24, pending Zaid's approval). The proposed agent is `qwen3.5:4b` (10/10 Arabic tool calls). The proposed extractor is `gemma4:e4b-it-qat` (95.9% field accuracy) with an injection guard (D7).
- The text crew report (10 fields with verbatim source spans, empty when unsupported) is **core** in build steps 5–6. Whisper voice stays an extra. The map-edit review is **thin** today: one draft plus one human approve button. (changed in U2)
- Pilot: Karak governorate. Today's showcase: the Qatraneh / Desert Highway corridor, on an "Approximate route" proxy.

**Rubric (verbatim from the organizers, Update 2 §2)**

| # | Scoring Area | Guidance | Weight |
|---|---|---|---|
| 1 | Challenge Alignment | Does the solution directly address the assigned one of the three tracks? | 10% |
| 2 | Problem & Impact | Is the problem meaningful, and does the solution create tangible value? | 15% |
| 3 | Functionality & Practicality | Does the live demo work? Is there a functional MVP? | 20% |
| 4 | Technical Quality & Execution | Is the implementation technically sound and appropriately scoped for 12 hours? | 15% |
| 5 | Innovation & Creativity | Is there an original approach or a clever application of existing technologies? | 20% |
| 6 | Open-Source AI Integration | Is an eligible open-weight model meaningfully integrated, rather than included superficially? | 15% |
| 7 | Privacy & Responsible Design | Are relevant data privacy, safety, and responsible-use considerations addressed? | 5% |

**Honesty rules for every task below**
- Every output carries one evidence label: Observed, Simulated, Hypothesis or Field-verified. Synthetic data is always Simulated. Typed demo entries are "Simulated · demo entry", never Field-verified.
- Candidates are inspection priorities, not accusations. The human decides.
- Numbers come only from the source files. Anything a source marks UNVERIFIED stays UNVERIFIED.

---

## 1. Research & data access verification (RES)

- [ ] ID: RES-01
  Task: [TODAY] Ask the JOSA hosts in writing what the judges' "time limit removed" means against the published 19:00 hacking end and 21:00 submission close. Also ask for the demo length, the judging format and the required submission fields (NEEDS-ZAID).
  Acceptance criteria: The organizer answer is saved with a timestamp in `docs/organizer-answers.md`, and DEMO-01 is cut to the confirmed demo length.
  Criteria served: Functionality & Practicality, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: RES-02
  Task: [TODAY] Ask the organizers in writing whether the team's earlier public exploration of this problem (named only in DEMO-05) fits the "pre-built work is banned" rule, given that everything is rebuilt today from freshly fetched public data (NEEDS-ZAID).
  Acceptance criteria: The written answer is saved in `docs/organizer-answers.md`, and the DEMO-05 wording follows it.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution (eligibility affects every criterion)
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: RES-03
  Task: [TODAY] (changed in U2) Get the organizers' list of eligible open-weight models. Ask whether custom-terms licences (for example Gemma terms or the Llama licence) count. Record the status of every model in MODELS.md.
  Acceptance criteria: Each MODELS.md role row shows eligibility as confirmed, pending or unknown, with the source of the answer.
  Criteria served: Open-Source AI Integration
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: RES-04
  Task: [TODAY] [U1] Build the problem-numbers card from sourced facts only:
  - NRW 41% (Aug 2026) and the 25%-by-2040 target (Petra)
  - 133,408 seized attacks on main and transmission lines, Jun 2013 to Jun 2026, and ~1,800 attacks on the Disi line in 2025 (Almamlaka)
  - the ~70% share of NRW from attacks on lines and sources, always phrased as a ministry estimate
  - renewable groundwater pumping ~391 MCM/yr vs safe yield ~274 MCM/yr (IIETA)

  The "105% of renewable water" claim is excluded.
  Acceptance criteria: Every number on screen, in the README and in the pitch has a source URL and date. 41% is never described as stolen water. The 70% figure always says "ministry estimate", and A8's wording check ("over" vs "about" 70%) is resolved against the source.
  Criteria served: Problem & Impact, Challenge Alignment
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: RES-05
  Task: [TODAY] [U1] Decide the dry-season Sentinel-2 time range. Earth Search's earliest item over the AOI is 2018-03-12, so "2017 →" (U1) is only possible through Planetary Computer's reprocessed L2A. Choose "2018 → latest" (Earth Search) or Planetary Computer for 2017.
  Acceptance criteria: The decision is recorded in `docs/PROVENANCE.md` with the STAC query used. The time slider (WEB-03) starts at the chosen year.
  Criteria served: Technical Quality & Execution, Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: RES-06
  Task: [U1] Close every fact marked UNVERIFIED in TECH_STACK.md and A2:
  - the dataset licences (Open-Meteo terms, CHIRPS, the Copernicus DEM licence text, WaPOR v3 coverage and level for Jordan)
  - a primary source for Jordan's pumping kWh/m³
  - the "~765 km of transmission lines" and "~32,000 km of network" scale numbers
  Acceptance criteria: Each item has an opened primary source in the register (DOC-05), or it stays labelled UNVERIFIED and out of the pitch. The energy parameter stays configurable until a source exists.
  Criteria served: Problem & Impact, Technical Quality & Execution, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: —
  Effort: M
  Owner: TBD

- [ ] ID: RES-07
  Task: [U1] Send formal data requests to the Karak water operator, WAJ and RJGC, covering:
  - the export CRS (EPSG:28191, EPSG:3066 or another)
  - the utility's import schema for map edits (U1 mentions a `wMain` target, unconfirmed)
  - who operates Karak distribution (the WAJ directorate or Aqaba Water Company)
  - whether the transmission mains are metered at both ends
  - network data, with permission to use it
  - the licensed wells and farms list
  Acceptance criteria: Each item has a written answer or a documented refusal. CRS and schema stay configurable until confirmed. No pipe or customer features are used without permission.
  Criteria served: Functionality & Practicality, Privacy & Responsible Design, Problem & Impact
  Priority: Should
  Evidence label of output: Observed
  Depends on: —
  Effort: L
  Owner: TBD

## 2. Data pipelines: ingestion, preprocessing, tiling, storage (PIPE)

- [ ] ID: PIPE-01
  Task: [TODAY] Fetch dry-season Sentinel-2 L2A for the Qatraneh AOI `[35.88, 31.19, 36.06, 31.28]` through STAC (no login), for each year in the RES-05 range. Store it under the E: data root.
  Acceptance criteria: There are per-year band files and a scene-ID log. Each download has a PROVENANCE.md row with URL and fetch time. Nothing comes from an earlier repo.
  Criteria served: Functionality & Practicality, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: RES-05, OPS-01
  Effort: M
  Owner: TBD

- [ ] ID: PIPE-02
  Task: [TODAY] [U1] Fetch the ancillary layers for the AOI:
  - CHIRPS v2.0 monthly plus Open-Meteo ERA5 rain and ET0, for the dry-month filter
  - ESA WorldCover v200 (2021), for the isolation feature
  - Copernicus DEM GLO-30, for elevations
  - a DEM elevation profile along the approximate route, for lift H
  Acceptance criteria: Clipped files on E:, a dry-month list and an elevation-profile JSON exist. Licence links, or UNVERIFIED, are recorded in DOC-03.
  Criteria served: Functionality & Practicality, Challenge Alignment, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: PIPE-03
  Task: [TODAY] [U1] Build the main-line "Approximate route" polyline along the Desert Highway through Qatraneh from OSM. If Overpass is down, use a hand-traced line labelled Simulated. No pipe features are downloaded (D5).
  Acceptance criteria: The GeoJSON carries the label "Approximate route" and an evidence label. The label appears on every map view and next to every proximity number.
  Criteria served: Functionality & Practicality, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Simulated
  Depends on: OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: PIPE-04
  Task: [TODAY] Pre-render Sentinel-2 dry-season PNG/WebP chips per site and year with rasterio, for the time slider and the before/after card. No live tiling.
  Acceptance criteria: The chips load in the app with Wi-Fi off, and each chip carries its scene ID and date.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: PIPE-01, L1-01
  Effort: S
  Owner: TBD

- [ ] ID: PIPE-05
  Task: [TODAY] Write the seed command (typer CLI). It loads Observed data and synthetic fixtures into SQLite on E:, with synthetic isolation:
  - generators write only to `data/synthetic/`
  - the seeder rejects synthetic files anywhere else
  - every synthetic row is labelled Simulated

  Also freeze `requirements-lock.txt`, and run every Python step with `PYTHONUTF8=1`.
  Acceptance criteria: One command seeds an empty DB. A test that moves a synthetic file outside `data/synthetic/` makes seeding fail. `requirements-lock.txt` is committed.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Simulated (fixtures) / Observed (fetched data)
  Depends on: DB-01
  Effort: S
  Owner: TBD

- [ ] ID: PIPE-06
  Task: Add a per-stage sha256 manifest, `pipeline_run` records and a `reproduce` command for the CPU stages (synthetic, twin, engine).
  Acceptance criteria: `reproduce` prints PASS per file, both locally and in CI (OPS-04).
  Criteria served: Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: PIPE-05
  Effort: M
  Owner: TBD

- [ ] ID: PIPE-07
  Task: Build Karak-governorate archives over the pilot bbox (35.33–36.22 E, 30.79–31.46 N):
  - Sentinel-2 over the full chosen range
  - Landsat 8/9 and HLS
  - FAO WaPOR, only if Jordan coverage is confirmed
  - per-site NDVI time series for forecasting
  Acceptance criteria: Each candidate site has a cached, STAC-sourced series tracked in the manifest. WaPOR is included only with confirmed coverage and licence.
  Criteria served: Functionality & Practicality, Innovation & Creativity
  Priority: Must
  Evidence label of output: Observed
  Depends on: RES-05, RES-06, PIPE-06
  Effort: L
  Owner: TBD

- [ ] ID: PIPE-08
  Task: Build an offline basemap: a PMTiles Protomaps Jordan extract with ODbL attribution and self-hosted glyph PBFs.
  Acceptance criteria: Arabic labels render with Wi-Fi off, and DevTools shows no requests to external hosts.
  Criteria served: Functionality & Practicality
  Priority: Should
  Evidence label of output: Observed
  Depends on: WEB-02
  Effort: M
  Owner: TBD

- [ ] ID: PIPE-09
  Task: Ingest NISAR (SME2/GCOV) and the GRACE-FO mascon with asf_search, earthaccess and h5py, subset to the pilot bbox. This needs an Earthdata login (NEEDS-ZAID). GCOV is about 1.8 GB per granule.
  Acceptance criteria: At least one NISAR granule subset and the GRACE-FO series are cached with provenance. Provisional products are labelled provisional.
  Criteria served: Innovation & Creativity, Problem & Impact
  Priority: Should
  Evidence label of output: Observed
  Depends on: PIPE-06
  Effort: L
  Owner: TBD

## 3. Layer 1: Source (field detection, change, volume, filter, GRACE check) (L1)

- [ ] ID: L1-01
  Task: [TODAY] Compute max-NDVI per dry season and ΔNDVI, then vectorize new-green polygons with `area_ha` and `first_seen`. Document the thresholds as assumptions. Keep an NDVI-threshold baseline, labelled as a baseline.
  Acceptance criteria: A GeoJSON with ≥ 1 candidate field, each citing scene IDs and dates. If none is found, say so honestly, and move the fusion case or label it Simulated (A2 risk).
  Criteria served: Challenge Alignment, Functionality & Practicality, Innovation & Creativity
  Priority: Must
  Evidence label of output: Hypothesis (irrigation inference over Observed imagery)
  Depends on: PIPE-01, PIPE-02
  Effort: M
  Owner: TBD

- [ ] ID: L1-02
  Task: [TODAY] [U1] Build the five features:
  - isolation: distance from ESA WorldCover cropland, documented as measuring "new", not "illegal"
  - proximity: distance to the approximate route, in coarse bins inside an uncertainty corridor
  - NDVI increase
  - persistence
  - size
  Acceptance criteria: Each feature is normalized to [0,1] and has a one-line definition. No proximity is ever shown as an exact metre figure.
  Criteria served: Technical Quality & Execution, Innovation & Creativity
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: L1-01, PIPE-03
  Effort: S
  Owner: TBD

- [ ] ID: L1-03
  Task: [TODAY] [U1] Build the transparent baseline score: 0.30·proximity_to_line + 0.25·isolation + 0.20·ndvi_increase + 0.15·persistence + 0.10·small_size. Present it as expert priors, not trained weights.
  Acceptance criteria: The API returns a per-site score with a per-feature breakdown, and the UI calls it "baseline".
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: L1-02
  Effort: S
  Owner: TBD

- [ ] ID: L1-04
  Task: [TODAY] [U1] Build the weight-sensitivity defense (A8):
  - run 1,000 random weightings (Dirichlet) and an equal-weights comparison (Spearman ρ)
  - flag sites as robust or weight-dependent
  - decide whether to drop or invert small_size, or replace it with estimated volume
  Acceptance criteria: A table of top-10 stability per site and the ρ value, shown in WEB-07 and on the Q&A sheet.
  Criteria served: Technical Quality & Execution, Innovation & Creativity
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: L1-03
  Effort: S
  Owner: TBD

- [ ] ID: L1-05
  Task: [TODAY] Estimate abstraction volume per field (ET0 × Kc range × area, with a dry-season rain check) as an m³ interval, and export LR(field) for the engine.
  Acceptance criteria: Each candidate has an m³ interval with source URLs stored, and BWB-01 consumes an LR(field) JSON.
  Criteria served: Problem & Impact, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Hypothesis (Observed inputs, assumed Kc)
  Depends on: L1-02, PIPE-02
  Effort: S
  Owner: TBD

- [ ] ID: L1-06
  Task: Build the false-positive filter:
  - a LightGBM classifier on field features (shape, seasonality, distance to canals and licensed areas, rain correlation)
  - a licensed-wells/farms import interface with a PII deny-list validator, using a synthetic placeholder until RES-07 delivers data
  Acceptance criteria: The classifier beats the L1-03 baseline on a labelled held-out set. An import file with an owner-name column is rejected, and the rejection is audited.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: PIPE-07, AIM-09, RES-07
  Effort: L
  Owner: TBD

- [ ] ID: L1-07
  Task: Run a GRACE-FO basin-level consistency check: the regional storage trend vs total estimated abstraction. State the limit: the mascon grid supports a Jordan-wide trend only, not Karak.
  Acceptance criteria: A plot and a one-line limit statement are on the Transparency page. GRACE is never used to score single sites.
  Criteria served: Innovation & Creativity, Problem & Impact
  Priority: Could
  Evidence label of output: Hypothesis
  Depends on: PIPE-09
  Effort: M
  Owner: TBD

## 4. Layer 2: Transmission fusion (tapping detection) (L2)

- [ ] ID: L2-01
  Task: [TODAY] Build a from-scratch WNTR twin of one transmission segment along the approximate route, with DEM elevations, flow meters, pressure sensors and an `assumptions.json`. The fallback is the analytic Hazen-Williams model in `spikes/A4_tap_detectability.py`.
  Acceptance criteria: The base run closes the mass balance within 0.1% with no negative pressures. All outputs are labelled Simulated.
  Criteria served: Technical Quality & Execution, Innovation & Creativity
  Priority: Must
  Evidence label of output: Simulated
  Depends on: PIPE-02, PIPE-03
  Effort: M
  Owner: TBD

- [ ] ID: L2-02
  Task: [TODAY] Inject a tap scenario, compute the flow-imbalance and pressure-gradient residuals, and turn them into LR(line).
  Acceptance criteria: The tap scenario shows a residual on the target segment, and BWB-01 consumes the LR(line) JSON.
  Criteria served: Innovation & Creativity, Functionality & Practicality
  Priority: Must
  Evidence label of output: Simulated
  Depends on: L2-01
  Effort: S
  Owner: TBD

- [ ] ID: L2-03
  Task: [TODAY] Build the fusion showcase on one Qatraneh segment: the field signal alone, the line signal alone, then the fused posterior.
  Acceptance criteria: Three posteriors with intervals and both signal labels render in WEB-04. The wording is "candidate for inspection".
  Criteria served: Innovation & Creativity, Functionality & Practicality
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: BWB-01
  Effort: S
  Owner: TBD

- [ ] ID: L2-04
  Task: Run a tap scenario sweep (size × position × pattern × noise) with residuals.
  Acceptance criteria: ≥ 200 runs, and a detection curve (P_d vs tap size at 1% false alarm) saved to `data/synthetic/`.
  Criteria served: Technical Quality & Execution
  Priority: Should
  Evidence label of output: Simulated
  Depends on: L2-01
  Effort: M
  Owner: TBD

- [ ] ID: L2-05
  Task: [U1] Replace the approximate route with real transmission geometry and meter data under a data agreement. Then extend the corridor to the Mudawwara (Ma'an) showcase once its geometry is confirmed.
  Acceptance criteria: The route label changes only when the source is Observed and permitted. The Mudawwara AOI runs through the same pipeline.
  Criteria served: Functionality & Practicality, Problem & Impact
  Priority: Should
  Evidence label of output: Observed
  Depends on: RES-07, PIPE-07
  Effort: L
  Owner: TBD

## 5. Layer 3: Distribution (twin, GNN, NISAR anomalies, unknown segments) (L3)

- [ ] ID: L3-01
  Task: Build a zone-aware distribution twin (elevation bands, inferred PRVs) and a leak/tap scenario library for training.
  Acceptance criteria: Pressures stay within 15–60 m in every band. Scenarios are stored in `data/synthetic/` with their seeds.
  Criteria served: Technical Quality & Execution
  Priority: Should
  Evidence label of output: Simulated
  Depends on: RES-07, PIPE-06
  Effort: L
  Owner: TBD

- [ ] ID: L3-02
  Task: Build a physics-informed GNN (PyTorch Geometric) for pressure reconstruction at unmonitored junctions and leak ranking. Build the classical residual-localization baseline first, and include a sensor-placement sensitivity study.
  Acceptance criteria: Hidden-node MAE and top-k hit rate beat the residual baseline on held-out locations. Results are labelled Simulated. No GNN claim is made anywhere before this passes.
  Criteria served: Open-Source AI Integration, Innovation & Creativity, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Simulated
  Depends on: L3-01
  Effort: XL
  Owner: TBD

- [ ] ID: L3-03
  Task: Build a NISAR L-band subsurface-moisture anomaly model over the network (rain-corrected, against a baseline), with Sentinel-1 C-band as a backup. It never claims depth or confirmation, and it notes that SME2 does not retrieve over urban areas.
  Acceptance criteria: The anomaly layer is labelled Hypothesis and lists its granule IDs. A limits note is on the Transparency page.
  Criteria served: Innovation & Creativity, Challenge Alignment
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: PIPE-09
  Effort: L
  Owner: TBD

- [ ] ID: L3-04
  Task: Infer undocumented segments and connections ("missing network knowledge") from twin residuals, field results and imagery.
  Acceptance criteria: Inferred segments appear only as dashed Hypothesis features, and they feed LRN-04 drafts.
  Criteria served: Innovation & Creativity
  Priority: Could
  Evidence label of output: Hypothesis
  Depends on: L3-02, LRN-04
  Effort: L
  Owner: TBD

## 6. Bayesian water-balance engine + priority metric + next-best measurement (BWB)

- [ ] ID: BWB-01
  Task: [TODAY] Build the Bayesian fusion: posterior odds = prior odds × LR(line) × LR(field), in closed form with NumPy/SciPy. Every factor is exposed to the UI.
  Acceptance criteria: A unit test shows that the posterior with both signals beats the posterior with either one alone. Every output carries an interval and an evidence label.
  Criteria served: Innovation & Creativity, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: L1-05, L2-02 (stubs allowed to start)
  Effort: M
  Owner: TBD

- [ ] ID: BWB-02
  Task: [TODAY] Build the priority metric: expected m³ recoverable per inspection hour = volume × P ÷ (travel + inspection hours), with an interval. Travel cost comes from NetworkX. The Ajloun tap at ~60 m³/hour (U1) is one cited example and a parameter range, never the default volume (A8).
  Acceptance criteria: The queue sorts by the metric's Quantity. The docs show the formula and the cited example, labelled Hypothesis.
  Criteria served: Problem & Impact, Innovation & Creativity
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: BWB-01
  Effort: S
  Owner: TBD

- [ ] ID: BWB-03
  Task: [TODAY] Build the next-best measurement: expected information gain (bits) over the top-N candidates and ≥ 3 measurement types.
  Acceptance criteria: A ranked list with bits, which changes after a learning update (LRN-01).
  Criteria served: Innovation & Creativity, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: BWB-01
  Effort: S
  Owner: TBD

- [ ] ID: BWB-04
  Task: [TODAY] Build the energy and CO₂ chain m³ → kWh → JD:
  - kWh/m³ = 0.002725 × H ÷ η, shown as a range with configurable inputs (H from PIPE-02)
  - CO₂ factor 529.79 g/kWh (2024, Ember via Our World in Data, per A4)
  Acceptance criteria: Every parameter shows its label and its source, or "assumed, configurable". There is no single national kWh/m³ claim.
  Criteria served: Challenge Alignment, Problem & Impact
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: PIPE-02
  Effort: S
  Owner: TBD

- [ ] ID: BWB-05
  Task: Build the full graph model (basin → wells → transmission lines → distribution zones → customers) in PyMC (needs Python ≥ 3.12) or NumPyro. It takes all three layers' likelihoods and outputs the loss-source breakdown (attributed vs unattributed).
  Acceptance criteria: Posteriors match the closed-form engine on the M0 case. New layers add likelihood factors without changing the ranking code.
  Criteria served: Innovation & Creativity, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: OPS-04, L3-02
  Effort: XL
  Owner: TBD

- [ ] ID: BWB-06
  Task: Make the next-best measurement cost-aware (EIG per cost) over segment hypotheses. Add logger readings, the ESP32 soil probe (MOB-04) and the forecast's "grow next season" prior (AIM-08).
  Acceptance criteria: It ranks ≥ 3 action types with their cost, and recomputes after a simulated logger reading.
  Criteria served: Innovation & Creativity
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: BWB-03, AIM-08
  Effort: M
  Owner: TBD

## 7. Learning loop: Verify and Remember (LRN)

- [ ] ID: LRN-01
  Task: [TODAY] Wire `ingest_field_result` → a new immutable posterior version → a live queue re-rank. An empty visit lowers the neighbouring hypotheses. Observed inputs never change. Typed entries are labelled "Simulated · demo entry".
  Acceptance criteria: The before/after rank is visible on screen within ≤ 5 s, and the posterior version goes up by 1. A DB test proves the Observed rows are unchanged.
  Criteria served: Innovation & Creativity, Functionality & Practicality
  Priority: Must
  Evidence label of output: Simulated (demo result) / Hypothesis (updated posterior)
  Depends on: BWB-01, DB-03
  Effort: M
  Owner: TBD

- [ ] ID: LRN-02
  Task: [TODAY] Build a demo reset that restores the seeded baseline state.
  Acceptance criteria: After a learning run, reset restores an identical queue (the hash of the queue JSON matches).
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Simulated
  Depends on: LRN-01, PIPE-05
  Effort: S
  Owner: TBD

- [ ] ID: LRN-03
  Task: [TODAY] [U1] (changed in U2) Build a thin "Remember": one confirmed demo finding becomes one dashed draft map edit with one human approve button. The approver must differ from the proposer, and the agent can never approve.
  Acceptance criteria: An approval by the proposer or by the agent returns 403. An audit row lists proposer, approver, time and evidence IDs. Nothing is applied before approval.
  Criteria served: Innovation & Creativity, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Simulated
  Depends on: LRN-01, DB-01, API-03
  Effort: S
  Owner: TBD

- [ ] ID: LRN-04
  Task: [U1] Build the full map-edit review:
  - approve or reject with a reason
  - a versioned layer
  - GeoJSON export in the configurable CRS, plus a WGS84 copy (RFC 7946)
  - an import-ready schema and an adapter layer
  Acceptance criteria: The export opens in QGIS in the right place in both CRSs. Rejected drafts keep their reason in the audit trail.
  Criteria served: Functionality & Practicality, Innovation & Creativity
  Priority: Should
  Evidence label of output: Simulated (until real field data exists)
  Depends on: LRN-03, RES-07
  Effort: L
  Owner: TBD

- [ ] ID: LRN-05
  Task: Add active learning:
  - choose the visits that most improve the model, and log retrain triggers
  - learn the baseline weights from labelled outcomes by logistic regression; synthetic labels only demonstrate the mechanism and are labelled Simulated
  - keep a change log: the LLM may write its text, but its numbers come from the engine
  Acceptance criteria: Learned weights replace the expert priors only when real outcome labels exist. Change-log numbers pass the AGT-03 checker.
  Criteria served: Innovation & Creativity, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: LRN-01, LRN-06 (for real labels; the synthetic mechanism comes first)
  Effort: L
  Owner: TBD

- [ ] ID: LRN-06
  Task: Run a field pilot with a utility in Karak: real inspections feed their results back. Only these outcomes may carry Field-verified.
  Acceptance criteria: A Field-verified row exists only with a field result from a logged-in crew member and an engineer's approval. A pilot report lists hits and empty visits.
  Criteria served: Problem & Impact, Functionality & Practicality
  Priority: Should
  Evidence label of output: Field-verified
  Depends on: RES-07, MOB-02, SEC-07
  Effort: XL
  Owner: TBD

## 8. Open-source AI models: fine-tuning, evaluation, baselines, model cards (AIM)

- [ ] ID: AIM-01
  Task: [TODAY] (changed in U2) Write MODELS.md per U2 §3 for the six roles: agent LLM, crew-report extractor, Arabic speech-to-text, irrigated-field detection, forecast, network/leak model. For each role, cover:
  - the candidates, and the pick based on measured results
  - the licence label (OSI vs custom terms) with a link
  - the weights tag and hash
  - VRAM and latency measured on the RTX 4060 8 GB
  - eligibility (RES-03)
  - the meaningful-integration test
  - the baseline to beat and its metric
  - today or later, the fallback, and the risks

  Add the three summary tables and the honest self-scores.
  Acceptance criteria: Zaid approves MODELS.md before any build past the current downloads. No row contains an unmeasured number.
  Criteria served: Open-Source AI Integration, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: AIM-02, RES-03
  Effort: M
  Owner: TBD

- [ ] ID: AIM-02
  Task: [TODAY] (changed in U2) Run a reproducible LLM bake-off. The contenders are Gemma 4 E4B and Qwen3.5-4B, plus Qwen3.5-9B if it fits in 8 GB with acceptable latency. The tests are:
  - 10 Arabic (incl. Jordanian dialect) tool-calling questions over the 6 tools
  - 10 dev crew reports
  - 3 refusal prompts
  - latency (first token and full answer) and peak VRAM

  If results are close, prefer an OSI licence.
  Acceptance criteria: The bake-off table is in MODELS.md, with exact prompts, tags and settings. Until that table exists, the agent and extractor LLM stays "pick per MODELS.md (bake-off pending: Gemma 4 E4B vs Qwen3.5-4B / Qwen3.5-9B)".
  Criteria served: Open-Source AI Integration, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: AIM-03
  Effort: M
  Owner: TBD

- [ ] ID: AIM-03
  Task: [TODAY] Set up the Ollama runtime (v0.40.10) with models on E: and these settings: `OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_KEEP_ALIVE=-1`, `OLLAMA_CONTEXT_LENGTH=8192`. Pull the bake-off contenders; each pull needs Zaid's OK.
  Acceptance criteria: `ollama show` lists tools for each contender, `ollama ps` shows GPU use, and the listener is bound to 127.0.0.1 only.
  Criteria served: Open-Source AI Integration, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: AIM-04
  Task: [TODAY] [U1] (changed in U2) Build the text crew-report extractor (core, build steps 5–6). The LLM picked per MODELS.md uses a JSON-schema `format` to return 10 fields, each with its verbatim source span:
  1. site / candidate ID
  2. location
  3. nearest asset
  4. observation type
  5. water use observed
  6. estimated flow / size
  7. evidence attached
  8. severity
  9. date and time
  10. crew notes / recommended action

  A code check blanks any field whose span is not an exact substring of the report.
  Acceptance criteria: Every filled field shows its exact source words. Unsupported fields stay empty. The JSON always validates.
  Criteria served: Open-Source AI Integration, Privacy & Responsible Design, Functionality & Practicality
  Priority: Must
  Evidence label of output: Simulated (synthetic reports)
  Depends on: AIM-02
  Effort: M
  Owner: TBD

- [ ] ID: AIM-05
  Task: [TODAY] [U1] (changed in U2) Build the offline fallback: a rule-based TypeScript extractor in the browser, with the same schema and the same span check, labelled "rule-based".
  Acceptance criteria: With Ollama stopped, a typed report still fills fields with spans, and the UI shows which extractor ran.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Simulated
  Depends on: WEB-01
  Effort: S
  Owner: TBD

- [ ] ID: AIM-06
  Task: [TODAY] Write model cards for the chosen LLM (and for Whisper if it is used): role, licence, weights tag, and eval numbers linked to the TEST outputs. Add a "what the AI does / does not do" panel.
  Acceptance criteria: Each number on a card links to a TEST-02 or TEST-03 output file.
  Criteria served: Open-Source AI Integration, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: TEST-02, TEST-03
  Effort: S
  Owner: TBD

- [ ] ID: AIM-07
  Task: [TODAY] [U1] Add the Whisper voice extra (build step 7): faster-whisper on CPU with `HF_HUB_OFFLINE=1`, feeding AIM-04. A pre-recorded clip and the typed path are the fallbacks.
  Acceptance criteria: A voice note fills the fields on screen. The transcript is shown before extraction. Latency is measured. Voice is never improvised live.
  Criteria served: Open-Source AI Integration, Functionality & Practicality
  Priority: Could
  Evidence label of output: Simulated
  Depends on: AIM-04, MOB-01
  Effort: S
  Owner: TBD

- [ ] ID: AIM-08
  Task: [U1] Forecast "sites likely to grow next season" with an open-weight time-series model (chronos-bolt-small or TimesFM 2.5; eligibility per RES-03). Compare it against a linear trend and naive persistence in a backtest (fit on earlier years, predict later years). Show it in a forecast panel with uncertainty.
  Acceptance criteria: MAE and interval coverage beat both baselines in the backtest. Otherwise the feature is cut (A8: with few annual points it would be theatre).
  Criteria served: Innovation & Creativity, Open-Source AI Integration
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: PIPE-07
  Effort: M
  Owner: TBD

- [ ] ID: AIM-09
  Task: Fine-tune Prithvi-EO-2.0 via TerraTorch (frozen encoder first, VRAM measured) on a labelled irrigated-field set with a spatial-block test split. The labels must not be threshold-derived, which would be circular.
  Acceptance criteria: F1/IoU beats the NDVI-threshold baseline on the spatial-block test, and the model card is published. Until then, Layer 1 is presented as the baseline.
  Criteria served: Open-Source AI Integration, Innovation & Creativity
  Priority: Should
  Evidence label of output: Hypothesis (detections) / Observed (eval)
  Depends on: PIPE-07
  Effort: XL
  Owner: TBD

## 9. Product AI agents: tools, grounding, evals, refusals (AGT)

- [ ] ID: AGT-01
  Task: [TODAY] Build six agent tools over the seed data, with a role-checked dispatcher and pydantic argument validation. Two tools change state: `create_work_order_draft` and `ingest_field_result`. Every tool call writes one audit row (who, tool, evidence IDs).
  Acceptance criteria: pytest shows that a disallowed role gets `not_permitted`. Outputs validate. The audit rows are visible in the admin view.
  Criteria served: Functionality & Practicality, Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Simulated
  Depends on: API-04, DB-02
  Effort: M
  Owner: TBD

- [ ] ID: AGT-02
  Task: [TODAY] Build one merged Analyst + Planner agent: a plain Python tool-calling loop over Ollama `/api/chat` (raw httpx), with a step cap and tool events streamed through `StreamingResponse` (text/event-stream). The LLM is picked per MODELS.md.
  Acceptance criteria: An Arabic question is answered live with the tool events visible in the UI, and an agent tool call visibly changes the UI state.
  Criteria served: Open-Source AI Integration, Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-01, AIM-03
  Effort: M
  Owner: TBD

- [ ] ID: AGT-03
  Task: [TODAY] Build the deterministic number checker (handles Arabic-Indic digits, ranges and rounding). Every number in a reply must equal a tool value and cite its evidence ID. A failing answer gets at most 2 rewrites, then a template answer, then "no evidence".
  Acceptance criteria: 40+ AR/EN checker strings pass, and a planted wrong number is rejected. No failing answer reaches the user unflagged.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design, Open-Source AI Integration
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-02
  Effort: M
  Owner: TBD

- [ ] ID: AGT-04
  Task: [TODAY] Add refusals and injection hardening:
  - templated refusals for legal conclusions and accusations, and for personal data or owner identity
  - crew notes and data wrapped as untrusted
  - an injection fixture ("ignore previous instructions…") that must not change tool use, and is flagged in the audit log
  Acceptance criteria: The refusal and injection eval items pass in TEST-02, and the refusal card renders in WEB-06.
  Criteria served: Privacy & Responsible Design, Open-Source AI Integration
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-02
  Effort: S
  Owner: TBD

- [ ] ID: AGT-05
  Task: [TODAY] Build the recorded-run fallback. It is recorded today with the chosen open-weight model only, badged "Recorded run" with a reason and a hash, and triggered when Ollama is stopped.
  Acceptance criteria: Stopping Ollama switches to the recording and shows the badge. Every recording stores the model name and digest. No closed-API output exists in the repo.
  Criteria served: Functionality & Practicality, Open-Source AI Integration
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-02
  Effort: S
  Owner: TBD

- [ ] ID: AGT-06
  Task: [TODAY] Build the work-order draft: from a case, a bilingual work order plus a simplified Arabic crew instruction. Suspected-tap orders carry a "coordinate with authorities" field. Only a human engineer approves.
  Acceptance criteria: Work-order numbers match the tool results (AGT-03). Approval is a human click by someone other than the requester.
  Criteria served: Functionality & Practicality, Open-Source AI Integration, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Hypothesis (case), with Observed copies of the tool numbers
  Depends on: AGT-01, SEC-02
  Effort: S
  Owner: TBD

- [ ] ID: AGT-07
  Task: [TODAY] [U1] (changed in U2) Build the text crew-report flow: a logged-in crew member types a report → AIM-04 extracts → the crew confirms → `ingest_field_result` → live re-rank.
  Acceptance criteria: Without a crew session the call returns 401. Only the crew's Confirm action creates a field result. The queue re-ranks (LRN-01).
  Criteria served: Functionality & Practicality, Open-Source AI Integration, Innovation & Creativity
  Priority: Must
  Evidence label of output: Simulated
  Depends on: AIM-04, LRN-01, API-03
  Effort: S
  Owner: TBD

- [ ] ID: AGT-08
  Task: Split the merged agent into the five agents from the brief (Analyst, Inspection Planner, Work-Order, Field Assistant, Learning), with role-filtered tool registries. This adds:
  - daily routes by m³/hour, and evidence packs
  - QR asset lookup, voice notes, a crew-confirm token and an "unavailable offline" state
  - a background Learning Agent that never overwrites Observed data
  Acceptance criteria: A crew-role conversation's tool list excludes restricted tools. A forced call to a denied tool is refused and audited. TEST-06 passes for each agent.
  Criteria served: Open-Source AI Integration, Functionality & Practicality
  Priority: Should
  Evidence label of output: Observed (behaviour) over Simulated data
  Depends on: AGT-07, API-05
  Effort: L
  Owner: TBD

## 10. Backend & API: FastAPI, auth, RBAC, audit (API)

- [ ] ID: API-01
  Task: [TODAY] Build the FastAPI 0.111 skeleton on 127.0.0.1:8000. It serves the Vite build from the same origin, uses a bilingual error envelope (a missing artifact gives an honest reason, never a 500), and has `/api/health` covering DB, model digest, data-file presence and the offline guard.
  Acceptance criteria: `/api/health` is green after `ops\start.ps1`. Removing a data file shows a bilingual reason instead of an error page.
  Criteria served: Technical Quality & Execution, Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: API-02
  Task: [TODAY] Build the `Quantity` pydantic type (value + interval + label + evidence_id) and use it for every number in every response.
  Acceptance criteria: A contract test fails when a response schema exposes a bare number outside an allowlist.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: API-01
  Effort: S
  Owner: TBD

- [ ] ID: API-03
  Task: [TODAY] Build auth: PyJWT HS256 in an HttpOnly cookie, stdlib scrypt password hashes, and the roles inspector, engineer and admin. Seed two engineer demo accounts, because the approver can never be the proposer. Demo credentials live in a gitignored local file.
  Acceptance criteria: Tests cover a wrong password (audited) and an expired token. The audit log shows distinct actors through the demo.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: DB-02
  Effort: S
  Owner: TBD

- [ ] ID: API-04
  Task: [TODAY] Build today's endpoints: queue, case and fusion evidence, imagery chips, next-best, field result, agent stream, extractor, and map-edit draft/approve. Add evidence lookup: any EV- ID returns value, interval, label, source and parents.
  Acceptance criteria: Every endpoint returns Quantities. Any EV- ID clicked in the UI resolves. Each restricted view writes an audit row.
  Criteria served: Functionality & Practicality, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: API-02, BWB-01
  Effort: M
  Owner: TBD

- [ ] ID: API-05
  Task: Add a policy file and an `authorize()` dependency (role × permission × sensitivity × region) as the one source of truth. Harden auth: argon2id, a CSRF header, refresh tokens and a login rate limit.
  Acceptance criteria: The RBAC table in the docs is generated from the policy file. A POST without CSRF is rejected. The rate limit is tested.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: API-03
  Effort: M
  Owner: TBD

- [ ] ID: API-06
  Task: Build the persona endpoint sets from the brief:
  - analyst: overview, trends, report export
  - engineer: scenario runs with progress events
  - crew: delta sync and idempotent result submit
  - admin: users and audit verify

  Add a watermarked evidence-pack PDF, an OpenAPI → TypeScript client, and schemathesis fuzzing.
  Acceptance criteria: The persona happy paths pass. Replaying a queued result creates exactly one field result. The web build fails on contract drift. Fuzzing finds no 5xx.
  Criteria served: Functionality & Practicality, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: API-05, DB-04
  Effort: L
  Owner: TBD

## 11. Database & storage (DB)

- [ ] ID: DB-01
  Task: [TODAY] Build the SQLite 3.42 schema with GeoJSON text columns. Its CHECK constraints and triggers reject:
  - a bad label
  - a value outside its interval
  - edits to evidence rows
  - an approver who is also the proposer
  - a map edit with no evidence
  - a report field with no source words

  The A5 spike already proved this approach.
  Acceptance criteria: Six negative tests each raise, and positive inserts pass.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-01
  Effort: M
  Owner: TBD

- [ ] ID: DB-02
  Task: [TODAY] Build the append-only audit log: BEFORE UPDATE/DELETE abort triggers, a SHA-256 hash chain, and a verify routine.
  Acceptance criteria: Tampering with one row in a test copy makes verify report the first broken sequence number.
  Criteria served: Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: DB-01
  Effort: S
  Owner: TBD

- [ ] ID: DB-03
  Task: [TODAY] Store immutable, versioned posteriors per engine run, with a diff query between two runs.
  Acceptance criteria: A new engine run never mutates earlier posteriors. The diff returns the rank changes that feed WEB-05's diff column.
  Criteria served: Technical Quality & Execution, Innovation & Creativity
  Priority: Must
  Evidence label of output: Observed
  Depends on: DB-01
  Effort: S
  Owner: TBD

- [ ] ID: DB-04
  Task: Move to PostgreSQL 17 + PostGIS 3.6.2 (portable, no admin rights):
  - Alembic migrations and GiST indexes
  - the DB-01 invariants ported as PostGIS triggers, plus synthetic → Simulated and "Field-verified requires a field result"
  - pg_dump/pg_restore demo snapshots
  Acceptance criteria: upgrade → downgrade → upgrade runs clean. All negative invariant tests raise. The PostGIS-backed queue ranks identically to the SQLite seed.
  Criteria served: Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-04
  Effort: L
  Owner: TBD

- [ ] ID: DB-05
  Task: Add Row-Level Security on cases, wells, network tables and field results, scoped by region and task.
  Acceptance criteria: A raw SQL select in a crew-scoped session returns only that crew's own-region, own-task rows.
  Criteria served: Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: DB-04
  Effort: M
  Owner: TBD

- [ ] ID: DB-06
  Task: Build raster and tile storage: COGs with a local STAC catalogue and PMTiles, all tracked in the manifest.
  Acceptance criteria: Every raster shown in the UI resolves to a catalogued asset with provenance.
  Criteria served: Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: DB-04, PIPE-07
  Effort: M
  Owner: TBD

## 12. Frontend web: Vite + React + TypeScript, MapLibre, RTL (WEB) (changed in U2)

- [ ] ID: WEB-01
  Task: [TODAY] (changed in U2) Build the Vite + React + TypeScript SPA shell (packages already installed in `web/`):
  - a hand-written `ar.ts` / `en.ts` dictionary, `<html lang dir>` switching and CSS logical properties
  - `fmt.ts` using `Intl.NumberFormat('ar-JO-u-nu-latn')`, with an interval formatter that throws when a label is missing
  Acceptance criteria: The toggle flips dir and lang. The formatter test renders 2400, 1100, 4000 as "2,400 (1,100–4,000)". FastAPI serves the build.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: WEB-02
  Task: [TODAY] Build the MapLibre map with a local plain style JSON (no online tiles): AOI, approximate route and candidate layers, with a legend by line style.
  Acceptance criteria: The map renders with the network disabled. Arabic labels are shaped. Layers toggle by keyboard. "Approximate route" is visible in the legend.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: WEB-01, PIPE-03
  Effort: M
  Owner: TBD

- [ ] ID: WEB-03
  Task: [TODAY] [U1] Build the time slider over the dry seasons (RES-05 range) from the pre-rendered chips, and a before/after evidence card for the Qatraneh showcase.
  Acceptance criteria: Sliding shows the new green patch appearing next to the route. Each frame shows its scene date and label.
  Criteria served: Innovation & Creativity, Functionality & Practicality, Problem & Impact
  Priority: Must
  Evidence label of output: Observed
  Depends on: WEB-02, PIPE-04
  Effort: M
  Owner: TBD

- [ ] ID: WEB-04
  Task: [TODAY] Build the fusion case view: two signal cards and the combined posterior, all with intervals and labels.
  Acceptance criteria: It matches L2-03, and every number has a badge and an interval.
  Criteria served: Innovation & Creativity, Functionality & Practicality
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: WEB-02, L2-03, UX-01
  Effort: M
  Owner: TBD

- [ ] ID: WEB-05
  Task: [TODAY] Build the priority queue (by m³ per inspection hour), the next-best panel, and submit-result → live re-rank with a diff column.
  Acceptance criteria: Submitting changes the order on screen within ≤ 5 s, instantly under reduced motion. The entry is labelled "Simulated · demo entry".
  Criteria served: Functionality & Practicality, Innovation & Creativity
  Priority: Must
  Evidence label of output: Hypothesis
  Depends on: API-04, LRN-01
  Effort: M
  Owner: TBD

- [ ] ID: WEB-06
  Task: [TODAY] Build the agent chat drawer: evidence chips, a tool-call drawer, a refusal card, and a runtime chip that says live or recorded run.
  Acceptance criteria: Every number in an answer is a chip linking to its evidence. A legal question shows the refusal card. The runtime chip is correct when Ollama is stopped.
  Criteria served: Open-Source AI Integration, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-02, AGT-05
  Effort: M
  Owner: TBD

- [ ] ID: WEB-07
  Task: [TODAY] [U1] Build the baseline vs model view: the baseline formula score next to the Bayesian posterior for the same sites, with the L1-04 robustness flags.
  Acceptance criteria: The same sites appear in both columns, with rank differences highlighted.
  Criteria served: Technical Quality & Execution, Innovation & Creativity
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: L1-04, BWB-01
  Effort: S
  Owner: TBD

- [ ] ID: WEB-08
  Task: [TODAY] Build the overview: a balance bar (attributed vs unattributed), 41% with its Petra source chip, and a static kWh estimate (no ticking counter).
  Acceptance criteria: Every number is labelled and sourced (RES-04).
  Criteria served: Problem & Impact, Challenge Alignment
  Priority: Should
  Evidence label of output: Observed (facts) / Hypothesis (estimates)
  Depends on: RES-04, BWB-04
  Effort: S
  Owner: TBD

- [ ] ID: WEB-09
  Task: [TODAY] [U1] (changed in U2) Build the thin map-edit screen: the dashed draft feature and one approve button. No reject flow and no export today.
  Acceptance criteria: The draft stays dashed until the second engineer approves it, and the audit row appears in the admin view.
  Criteria served: Innovation & Creativity, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Simulated
  Depends on: LRN-03, WEB-02
  Effort: S
  Owner: TBD

- [ ] ID: WEB-10
  Task: Build the remaining brief screens for analysts and engineers:
  - a national overview with three layer toggles
  - a network twin view (pipes, junctions, reconstructed pressures, leak hypotheses)
  - the forecast panel (AIM-08)
  - an impact dashboard (m³, kWh, JD, trend vs the 25% target)
  - a learning-loop view
  Acceptance criteria: Each screen uses only labelled Quantities, and Playwright covers each one.
  Criteria served: Functionality & Practicality, Problem & Impact
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: L3-02, BWB-05, AIM-08
  Effort: L
  Owner: TBD

- [ ] ID: WEB-11
  Task: Build the admin screens (users, roles, regions, audit log browse and verify) and the work-order screens (create, approve, track). Migrate to i18next + react-i18next, with an accessible component set (react-aria-components, or shadcn/ui with RTL).
  Acceptance criteria: The full work-order lifecycle is demo-able, and an admin cannot grant itself the engineer role.
  Criteria served: Functionality & Practicality, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: API-05
  Effort: L
  Owner: TBD

## 13. Mobile crew app: PWA, offline (MOB)

- [ ] ID: MOB-01
  Task: [TODAY] [U1] (changed in U2) Build the crew view at 390 px on localhost:
  - a task card with three result buttons (≥ 48 px)
  - the text report screen: a typed Jordanian-Arabic report fills the 10 fields with the source words highlighted, and empty fields are marked "no evidence"
  Acceptance criteria: Usable at 360 and 390 px, with simple Arabic copy. The confirmed result feeds WEB-05.
  Criteria served: Functionality & Practicality, Open-Source AI Integration
  Priority: Must
  Evidence label of output: Simulated
  Depends on: AGT-07, AIM-05
  Effort: M
  Owner: TBD

- [ ] ID: MOB-02
  Task: Build the full offline-first PWA (vite-plugin-pwa + dexie), served over local HTTPS so the phone is a secure context, with an offline queue and sync.
  Acceptance criteria: On a real phone, `isSecureContext` is true, the service worker registers, and a result entered in airplane mode syncs once on reconnect.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: API-06
  Effort: L
  Owner: TBD

- [ ] ID: MOB-03
  Task: Add QR asset lookup with the camera, photo capture with EXIF stripped on upload, and voice notes through AIM-07.
  Acceptance criteria: A QR scan resolves an asset, and a test proves uploaded photos carry no EXIF.
  Criteria served: Functionality & Practicality, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: MOB-02
  Effort: M
  Owner: TBD

- [ ] ID: MOB-04
  Task: [U1] Build the optional field device: ESP32 + soil-moisture sensor + GPS, placed by crews at candidate sites. It sends readings to the crew app as a next-best measurement type.
  Acceptance criteria: Readings arrive with device ID and timestamp, and appear in BWB-06 as a measurement option.
  Criteria served: Innovation & Creativity, Functionality & Practicality
  Priority: Could
  Evidence label of output: Observed
  Depends on: MOB-02
  Effort: L
  Owner: TBD

## 14. UI/UX design system (UX)

- [ ] ID: UX-01
  Task: [TODAY] Pass the design-brief gate (build step 1). Then build a static HTML mockup of the fusion case (RTL, tokens, labelled fixtures) for Zaid's approval. Use CSS-variable tokens and self-hosted fonts via Fontsource (family per the brief, no CDN at demo time).
  Acceptance criteria: Zaid approves the mockup. It opens in Chrome with `dir="rtl"`, no mojibake, the Arabic font rendering, and a badge and interval on every number.
  Criteria served: Functionality & Practicality, Innovation & Creativity
  Priority: Must
  Evidence label of output: Simulated (fixtures)
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: UX-02
  Task: [TODAY] Build the evidence-label badge component (Observed / Simulated / Hypothesis / Field-verified) for every number and map layer, with a persistent legend. Wrap mixed number + unit spans in `<bdi>`.
  Acceptance criteria: A visual and grep check finds no unlabelled number in any view.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: WEB-01
  Effort: S
  Owner: TBD

- [ ] ID: UX-03
  Task: [TODAY] [U1] Build the honesty/transparency panel, and carry the Detect · Verify · Remember framing through navigation and copy. The panel covers:
  - the route is approximate
  - the crew reports are synthetic
  - a candidate is not a violation
  - Sentinel-2 sees surface water use only; subsurface needs NISAR
  - per layer, what we observe, simulate, hypothesize and have verified
  Acceptance criteria: The panel text matches the README and the pitch exactly.
  Criteria served: Privacy & Responsible Design, Challenge Alignment
  Priority: Must
  Evidence label of output: Observed
  Depends on: DOC-03
  Effort: S
  Owner: TBD

- [ ] ID: UX-04
  Task: Add dark mode, contrast and colour-vision checks, keyboard paths and reduced motion, with @axe-core/playwright in CI.
  Acceptance criteria: axe reports no serious violations on the main views, and dark mode keeps badge contrast.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: OPS-04
  Effort: M
  Owner: TBD

- [ ] ID: UX-05
  Task: Map persona journeys and the full screen inventory for the five personas (ministry analyst, network engineer, inspector, field crew, admin), covering every brief screen plus the crew app.
  Acceptance criteria: Each persona has a mapped journey, and every screen in WEB-10, WEB-11 and MOB-02 traces back to one.
  Criteria served: Functionality & Practicality, Problem & Impact
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: —
  Effort: M
  Owner: TBD

## 15. Security, privacy & responsible AI (SEC)

- [ ] ID: SEC-01
  Task: [TODAY] Keep everything local and free of personal data:
  - bind every service to 127.0.0.1
  - turn telemetry off: `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `OLLAMA_NO_CLOUD=1`
  - never download customer or parcel layers, and use internal IDs only
  - add a PII deny-list test over the schema
  Acceptance criteria: `Get-NetTCPConnection` shows loopback listeners only, and the schema test finds no name-like columns.
  Criteria served: Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: DB-01
  Effort: S
  Owner: TBD

- [ ] ID: SEC-02
  Task: [TODAY] Enforce role gates:
  - candidate taps and wells are visible only to authorized roles, and every view and export is audited
  - the approver differs from the proposer for work orders and map edits, and the agent cannot approve
  - rehearse a privacy beat that shows a denied request and its audit row live
  Acceptance criteria: Tests show 403 for an unauthorized role on sensitive layers, for self-approval, and for agent approval.
  Criteria served: Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: API-03, DB-02
  Effort: S
  Owner: TBD

- [ ] ID: SEC-03
  Task: [TODAY] Prioritization, not accusation. Wording is always "candidate for inspection" or "unexplained use". A banned-phrase check (confirmed-wrongdoing claims in Arabic and English, accusations, legal conclusions) runs over UI strings, agent output and docs.
  Acceptance criteria: The banned-phrase check passes on the repo and on the TEST-02 agent outputs.
  Criteria served: Privacy & Responsible Design, Problem & Impact
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-03
  Effort: S
  Owner: TBD

- [ ] ID: SEC-04
  Task: [TODAY] Keep the repo clean: no secrets (none are needed today), no restricted geometry or exact candidate coordinates in git, a secret scan before any push, and generalized geometry in the public video.
  Acceptance criteria: The secret scan is clean on the final diff, and the public video shows no exact candidate coordinates.
  Criteria served: Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: SEC-05
  Task: Write a threat model covering the "vandal's guide" risk of a corridor map of candidate taps, insider misuse, prompt injection and data exfiltration, with each mitigation mapped to a task.
  Acceptance criteria: The threat-model doc is reviewed, and every high risk maps to a task ID.
  Criteria served: Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Hypothesis
  Depends on: —
  Effort: M
  Owner: TBD

- [ ] ID: SEC-06
  Task: Add a socket-level offline guard (`pytest -m offline`) and an RBAC matrix test generated from the policy file (role × endpoint × region).
  Acceptance criteria: A non-loopback connect attempt is blocked and logged. CI fails on an unlisted route.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: API-05, OPS-04
  Effort: M
  Owner: TBD

- [ ] ID: SEC-07
  Task: Write the governance documents:
  - a data-in-country deployment plan
  - a data-sharing agreement template with the utility
  - a retention policy
  - a responsible-use policy: the human decides, suspected taps are handled with the authorities, and empty visits are recorded
  Acceptance criteria: The documents are reviewed with the pilot utility before LRN-06 starts.
  Criteria served: Privacy & Responsible Design, Challenge Alignment
  Priority: Should
  Evidence label of output: Observed
  Depends on: RES-07
  Effort: M
  Owner: TBD

## 16. Testing & validation (TEST)

- [ ] ID: TEST-01
  Task: [TODAY] Build the backend suite with pytest 9 + httpx: DB invariant negative tests, engine unit tests (fusion monotonicity, intervals) and RBAC denials.
  Acceptance criteria: The suite is green on the seeded DB.
  Criteria served: Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: DB-01, BWB-01, SEC-02
  Effort: S
  Owner: TBD

- [ ] ID: TEST-02
  Task: [TODAY] Build the agent eval mini-set: 12 Arabic/English items (`pytest -m llm`) plus 40+ number-checker strings, with a JSON report holding all metrics and the model digest.
  Acceptance criteria: The report file exists, and the hallucinated-number count is reported honestly in the README.
  Criteria served: Open-Source AI Integration, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: AGT-03, AGT-04
  Effort: S
  Owner: TBD

- [ ] ID: TEST-03
  Task: [TODAY] [U1] (changed in U2) Evaluate the extractor on a frozen held-out set of synthetic Jordanian-Arabic reports (target ≥ 25, ideally 50+). The reports are written by someone who did not write the prompts or rules. Measure field accuracy, empty-when-unsupported accuracy, span validity and hallucinated fills, LLM vs rules. The earlier prototype's figure in U1 §3.4 is a target to beat: it is re-measured today and never quoted as ours.
  Acceptance criteria: A results table with the test-set n is in the README and MODELS.md.
  Criteria served: Open-Source AI Integration, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Simulated (data) / Observed (metrics)
  Depends on: AIM-04, AIM-05
  Effort: M
  Owner: TBD

- [ ] ID: TEST-04
  Task: [TODAY] Add the vitest check (the formatter refuses any number without a label and an interval) and one Playwright smoke test of the demo path.
  Acceptance criteria: Both pass on the frozen build.
  Criteria served: Technical Quality & Execution, Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: WEB-01, WEB-05
  Effort: S
  Owner: TBD

- [ ] ID: TEST-05
  Task: [TODAY] Measure the resource budget under full demo load (LLM + Chrome + screen recorder): VRAM, RAM, first-token latency and re-rank time.
  Acceptance criteria: A measured table is in the docs. Peak RAM < 13 GB, VRAM < 7.5 GB and re-rank ≤ 5 s (the A5 and TECH_STACK targets), or the failing item is cut.
  Criteria served: Functionality & Practicality, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: AGT-02, LRN-01
  Effort: S
  Owner: TBD

- [ ] ID: TEST-06
  Task: Expand the agent evaluation to 30+ Arabic and English questions with expected grounded answers (brief §8), then to A7's 48-item set with a keyword baseline. Track accuracy and hallucination rate per release.
  Acceptance criteria: An LLM vs baseline table is on the Transparency page, with a regression gate in CI.
  Criteria served: Open-Source AI Integration
  Priority: Should
  Evidence label of output: Observed
  Depends on: TEST-02, OPS-04
  Effort: M
  Owner: TBD

- [ ] ID: TEST-07
  Task: Build the metric suite for the later models:
  - Prithvi vs NDVI: F1/IoU on spatial blocks
  - GNN vs residual: top-k and hidden-node MAE
  - forecast vs linear trend: MAE and interval coverage
  Acceptance criteria: Each metric is reproducible from the PIPE-06 manifests and linked from its model card.
  Criteria served: Technical Quality & Execution, Open-Source AI Integration
  Priority: Should
  Evidence label of output: Observed
  Depends on: AIM-08, AIM-09, L3-02
  Effort: M
  Owner: TBD

## 17. DevOps & local deployment: offline demo mode, seed data; no Docker today (OPS)

- [ ] ID: OPS-01
  Task: [TODAY] Create a fresh git repo today (author Zaid Abu Alshaar) with `docs/PROVENANCE.md`. It states that all code was written on 2026-10-24, and lists every dataset's URL and download time. Nothing is copied from earlier repos.
  Acceptance criteria: The first commit in `git log` is on 2026-10-24, after the event start. PROVENANCE.md covers every dataset in PIPE-01 to PIPE-04.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: OPS-02
  Task: [TODAY] Build the one-command start, `ops\start.ps1`: it sets the env, seeds SQLite on E:, starts uvicorn on 127.0.0.1:8000 and opens Chrome.
  Acceptance criteria: One command takes a cold start to a green `/api/health`, and the time is measured.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: API-01, PIPE-05
  Effort: S
  Owner: TBD

- [ ] ID: OPS-03
  Task: [TODAY] Run the freeze gate: no new npm packages after 17:30, feature freeze at ~18:00, a smoke test, and a Wi-Fi-off end-to-end test before 18:30.
  Acceptance criteria: A logged Wi-Fi-off run of the full demo path, and a tagged freeze commit.
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: TEST-04, OPS-02
  Effort: S
  Owner: TBD

- [ ] ID: OPS-04
  Task: Move to a uv-managed Python venv on E: (it avoids the sitecustomize shadowing landmine), and add GitHub Actions CI (invariants, RBAC, contract, agent unit tests, reproduce) on synthetic data only.
  Acceptance criteria: CI is green on main from a clean clone.
  Criteria served: Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: PIPE-06
  Effort: M
  Owner: TBD

- [ ] ID: OPS-05
  Task: Build a reference deployment (PostGIS, API, Ollama) with Docker Engine or Podman on Linux. Not Docker Desktop, whose licence charges large and government organisations.
  Acceptance criteria: compose up gives a green health check on synthetic data in CI.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: DB-04
  Effort: M
  Owner: TBD

- [ ] ID: OPS-06
  Task: Write an on-prem install guide for a ministry or utility server: measured GPU/RAM sizing, the model-serving option (Ollama or vLLM), backups, the update path, and no external telemetry.
  Acceptance criteria: Someone outside the team completes a clean install using only the guide.
  Criteria served: Problem & Impact, Privacy & Responsible Design
  Priority: Could
  Evidence label of output: Observed
  Depends on: OPS-05
  Effort: M
  Owner: TBD

## 18. Demo, pitch & judge defense (DEMO)

- [ ] ID: DEMO-01
  Task: [TODAY] Write the demo script, mapped to the criteria and cut to the RES-01 length:
  1. the problem: 41%, the 25% target, attacks on lines
  2. the Qatraneh time slider
  3. the fusion case
  4. the queue by m³/hour
  5. the next-best measurement
  6. the agent in Arabic, with evidence chips
  7. a text crew report
  8. the live re-rank
  9. the thin map-edit approval
  10. energy and transparency
  Acceptance criteria: Each beat names its evidence label aloud, and the script fits the confirmed length.
  Criteria served: Functionality & Practicality, Innovation & Creativity, Challenge Alignment
  Priority: Must
  Evidence label of output: Observed
  Depends on: RES-01
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-02
  Task: [TODAY] Build a presenter bar (←/→ through the steps, reset demo state via LRN-02) and hold two full rehearsals.
  Acceptance criteria: Two full runs complete without a reload.
  Criteria served: Functionality & Practicality
  Priority: Should
  Evidence label of output: Observed
  Depends on: LRN-02, WEB-05
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-03
  Task: [TODAY] Record the backup video with FFmpeg 9.0.2 screen capture (test gdigrab once; `drawtext` needs `fontfile=`).
  Acceptance criteria: The video plays offline, and candidate coordinates are generalized (SEC-04).
  Criteria served: Functionality & Practicality
  Priority: Must
  Evidence label of output: Observed
  Depends on: OPS-03
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-04
  Task: [TODAY] Write the judge Q&A sheet from A8's twelve hostile questions and brief §12:
  - prior work and the pre-built rule
  - "Is 41% stolen water?" and "Can a satellite prove a tap?"
  - "Why these weights?" and the approximate route
  - how we differ from ASTERRA, without "leaks only" or "first system" claims (A8)
  - the pipe-data licence
  - meaningful vs decorative AI, and model eligibility
  - what happens on an empty visit, and vandal misuse
  - energy, who pays, and how it scales
  Acceptance criteria: Each answer cites a source or a task output. Arabic and English versions are rehearsed.
  Criteria served: Problem & Impact, Open-Source AI Integration, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: L1-04, AIM-01
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-05
  Task: [TODAY] Add a one-line prior-work disclosure to the submission. Draft (final wording per RES-02): "The team explored this problem before the event in the public repos kurdim12/missing-blue and aboodhaymouni/missing-blue (AI Quest 2026) and ZaidAbuAlshaar/mizan (AstroCode); no code, data or assets from them were reused, and Blue Balance was written, and its data fetched, on 2026-10-24."
  Acceptance criteria: The line appears once in the submission and once in the README. The earlier names appear nowhere else in the repo, UI or slides.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: RES-02, OPS-01
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-06
  Task: [TODAY] Submit a rough version on the MLH "Submit a Project" page by 18:00, and the final version before 21:00 (NEEDS-ZAID: MyMLH login).
  Acceptance criteria: A submission confirmation is visible for both, and the final version includes DEMO-05.
  Criteria served: Functionality & Practicality (eligibility for every criterion)
  Priority: Must
  Evidence label of output: Observed
  Depends on: DEMO-05, OPS-03
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-07
  Task: [TODAY] [U1] Write the pitch and slide content:
  - lead with 133,408 attacks on main and transmission lines since 2013, and ~1,800 on the Disi line in 2025
  - "one tap can draw ~60 m³/hour" as a cited example
  - "The satellite detects. The crew verifies. The map remembers."
  - the honest answers from U1 §6
  - a claim / don't-claim slide, and a roadmap slide that marks not-built items
  - a careful tone, given today's news from Karak (A2)
  Acceptance criteria: A claims pass shows that every number on the slides matches RES-04 and its source.
  Criteria served: Problem & Impact, Challenge Alignment, Innovation & Creativity
  Priority: Must
  Evidence label of output: Observed
  Depends on: RES-04
  Effort: S
  Owner: TBD

- [ ] ID: DEMO-08
  Task: Build a post-event pilot pitch pack for the ministry or utility: who pays, how it scales in Jordan, differentiation, the M1–M5 roadmap, and the privacy posture.
  Acceptance criteria: The team has reviewed it, and every number is sourced or labelled.
  Criteria served: Problem & Impact, Challenge Alignment
  Priority: Should
  Evidence label of output: Observed
  Depends on: RES-06, SEC-07
  Effort: M
  Owner: TBD

## 19. Documentation & licensing (DOC)

- [ ] ID: DOC-01
  Task: [TODAY] (changed in U2) Apply the final name "Blue Balance (ميزان الأزرق)" in the UI, code, repo, docs, `brand/` and slides. Sync TECH_STACK.md with U2 §1: the title, D2, the E: data-root folder name, D4 → "pick per MODELS.md", the text crew report moved into steps 5–6, and the thin map-edit review.
  Acceptance criteria: A grep for the earlier names over the repo, docs and `brand/` returns only the DEMO-05 line. TECH_STACK.md and this file agree.
  Criteria served: Challenge Alignment, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: —
  Effort: S
  Owner: TBD

- [ ] ID: DOC-02
  Task: [TODAY] Write the README:
  - "what we claim / don't claim" and setup
  - data sources and licences, saying "no licence stated" or UNVERIFIED where true
  - links to the model cards
  - the roadmap (Prithvi, GNN, NISAR, GRACE, forecasting, PostGIS, full PWA, Docker/Podman), clearly marked "not built"
  Acceptance criteria: No TODO, lorem or FIXME, and every number is sourced.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Must
  Evidence label of output: Observed
  Depends on: AIM-06, DOC-03
  Effort: S
  Owner: TBD

- [ ] ID: DOC-03
  Task: [TODAY] Write the data-sources card (URL, licence, fetch time, evidence label) for every layer. It feeds the Transparency page.
  Acceptance criteria: Every dataset in PIPE-01 to PIPE-04 is listed, and the card matches PROVENANCE.md.
  Criteria served: Privacy & Responsible Design, Technical Quality & Execution
  Priority: Must
  Evidence label of output: Observed
  Depends on: PIPE-02, PIPE-03
  Effort: S
  Owner: TBD

- [ ] ID: DOC-04
  Task: [TODAY] Write the "Physics & limits" card: the fusion formula, the energy formula, the thresholds, the approximate-route caveat, and what we cannot see.
  Acceptance criteria: It is on the Transparency page, with no unsourced constant.
  Criteria served: Technical Quality & Execution, Privacy & Responsible Design
  Priority: Should
  Evidence label of output: Observed
  Depends on: L2-02, BWB-04
  Effort: S
  Owner: TBD

- [ ] ID: DOC-05
  Task: Pick an OSI open-source licence for the repo (Zaid decides). Build a third-party licence inventory (backend, frontend, models, datasets, including the psycopg LGPL note) and a model licence register that excludes non-commercial or use-restricted models (A3 flagged OlmoEarth and Command R7B Arabic).
  Acceptance criteria: A LICENSE file is committed. The register lists every dependency, model and dataset with a link and a commercial-use answer.
  Criteria served: Open-Source AI Integration, Privacy & Responsible Design, Technical Quality & Execution
  Priority: Should
  Evidence label of output: Observed
  Depends on: RES-06
  Effort: S
  Owner: TBD

- [ ] ID: DOC-06
  Task: Write the architecture doc with an ERD and the generated RBAC table, data cards per dataset, and model cards for every later model (forecast, Prithvi, GNN).
  Acceptance criteria: Every version in the docs has a source (lockfile or URL), and each model card links to TEST-07 outputs.
  Criteria served: Technical Quality & Execution, Open-Source AI Integration
  Priority: Should
  Evidence label of output: Observed
  Depends on: DB-04, TEST-07
  Effort: M
  Owner: TBD

---

## Milestones (ordered)

### M0: Today, the 8 build steps (see [TECH_STACK.md §10](TECH_STACK.md))
All [TODAY] tasks, grouped by build step. Hacking ends at 19:00, and the final submission goes in before 21:00.

| Build step | Tasks |
|---|---|
| 1. Approvals | UX-01 (design brief), AIM-01 (MODELS.md approval), RES-01, RES-02, RES-03, DOC-01 |
| 2. Skeleton | OPS-01, API-01, API-02, API-03, DB-01, DB-02, DB-03, WEB-01, PIPE-05, OPS-02, SEC-01, SEC-04 |
| 3. Data | RES-05, PIPE-01, PIPE-02, PIPE-03, PIPE-04, L1-01 |
| 4. Engine | L1-02, L1-03, L1-04, L1-05, L2-01, L2-02, L2-03, BWB-01, BWB-02, BWB-03, BWB-04 |
| 5. AI (text crew report is core here, changed in U2) | AIM-02, AIM-03, AIM-04, AIM-05, AIM-06, AGT-01 to AGT-07, TEST-02, TEST-03 |
| 6. UI (text crew report screen and thin map-edit review, changed in U2) | API-04, WEB-02 to WEB-09, UX-02, UX-03, MOB-01, LRN-01, LRN-02, LRN-03, SEC-02, SEC-03, RES-04 |
| 7. Extras | AIM-07 (Whisper voice) |
| 8. Freeze | OPS-03, TEST-01, TEST-04, TEST-05, DEMO-01 to DEMO-07, DOC-02, DOC-03, DOC-04 |

**Demo-able outcome:** a Wi-Fi-off demo of the Qatraneh corridor on the "Approximate route" proxy. A green patch appears on the time slider. The fusion case raises one segment's posterior. The queue ranks by expected m³ per inspection hour, with the next-best measurement. The open-weight agent answers in Arabic with clickable evidence. A typed crew report fills the 10 fields with source spans. The queue re-ranks live. A second engineer approves one dashed map edit. Everything carries labels and intervals, there is a recorded backup video, and the submission includes the disclosure line.

### M1: Hardening and reproducibility (post-event)
Tasks: RES-06, RES-07 (start the data requests early, because they are slow), PIPE-06, DB-04, API-05, API-06, SEC-05, SEC-06, OPS-04, TEST-06, UX-04, UX-05, WEB-11, DOC-05, DOC-06.
**Demo-able outcome:** a clean clone gives green CI and `reproduce` PASS. The PostGIS-backed queue ranks the M0 sites identically to the SQLite seed. The admin view verifies the audit chain, and the expanded agent eval table is published.

### M2: Source layer at scale and the AI upgrades
Tasks: PIPE-07, PIPE-08, PIPE-09, L1-06, L1-07, AIM-08, AIM-09, TEST-07.
**Demo-able outcome:** a Karak-wide candidate map on an offline basemap, with a Prithvi vs NDVI-baseline table (spatial-block test). A forecast panel shows "sites likely to grow next season" beside its linear-trend backtest, or a documented decision to cut it.

### M3: Distribution layer
Tasks: L2-04, L3-01, L3-02, L3-03, L3-04, BWB-05, WEB-10, DB-06.
**Demo-able outcome:** a network twin view with reconstructed pressures and ranked leak hypotheses, and a GNN vs residual-baseline top-k table (Simulated). A NISAR moisture-anomaly overlay (Hypothesis) and the loss-source breakdown come from the full graph model.

### M4: Verify and Remember, complete
Tasks: MOB-02, MOB-03, MOB-04, AGT-08, LRN-04, LRN-05, BWB-06, DB-05.
**Demo-able outcome:** a phone in airplane mode records a voice report, scans a QR asset and syncs on reconnect, and the ranking updates. An approved map edit (with a reject-with-reason path) exports in both CRSs and opens in QGIS. The five agents run with role-filtered tools.

### M5: Pilot and deployment
Tasks: L2-05, OPS-05, OPS-06, SEC-07, LRN-06, DEMO-08.
**Demo-able outcome:** an on-prem install at a utility on Docker Engine or Podman, with data kept in-country. Real field results become the first Field-verified rows and recalibrate the weights (LRN-05).

---

## Team split proposal

The brief's default was 4 people (data/geospatial, AI/ML, backend + agents, frontend/UX). For a team of 3, I propose the split below. The Owner fields in the tasks stay "TBD" until Zaid confirms.

| Person | Role | Proposed categories (today → later) |
|---|---|---|
| **Zaid Abu Alshaar** | Software and integration lead | Today: RES-01 to RES-03 (organizer questions, NEEDS-ZAID), RES-04, UX, WEB, MOB-01, OPS-01 to OPS-03, DEMO, DOC, the approval gates (UX-01, AIM-01) and the final submission. Later: WEB-10, WEB-11, UX-04, UX-05, OPS-04 to OPS-06, DEMO-08. |
| **Abdalrahman Al-Kurdi** | AI and backend | Today: AIM-02 to AIM-06, AGT, API, DB, BWB-01 to BWB-03, LRN, SEC-01 to SEC-03, TEST-01, TEST-02. Later: AIM-08, AIM-09, AGT-08, API-05, API-06, DB-04 to DB-06, BWB-05, BWB-06, LRN-04, LRN-05, L3-02, TEST-06, TEST-07. |
| **Abdalrahman Al-Haymouni** | Hardware | Today: data and physics, i.e. PIPE-01 to PIPE-05, L1-01 to L1-05, the WNTR twin (L2-01 to L2-03), energy (BWB-04), the resource budget (TEST-05), the Wi-Fi-off run (OPS-03) and video capture (DEMO-03). He also writes the TEST-03 held-out reports, because the evaluator must not be the prompt author (A8). Later: MOB-04 (ESP32 device), MOB-02 and MOB-03 on real phones, L2-04, L2-05, L3-01, L3-03, PIPE-07 to PIPE-09, LRN-06 field logistics. |

---

## Criteria coverage matrix (criterion × milestone)

● = this milestone directly raises the criterion · ○ = supports it · — = little change. The marks are qualitative; no scores are claimed here (the self-scores live in MODELS.md, AIM-01).

| Criterion (weight) | M0 Today | M1 Hardening | M2 Source at scale | M3 Distribution | M4 Verify & Remember | M5 Pilot |
|---|---|---|---|---|---|---|
| Challenge Alignment (10%) | ● energy and CO₂ (BWB-04), green-track framing (UX-03, DEMO-07) | — | ○ Karak-wide Layer 1 (PIPE-07) | ○ NISAR (L3-03) | ○ field device (MOB-04) | ● in-country deployment (SEC-07, OPS-06) |
| Problem & Impact (15%) | ● sourced numbers (RES-04), m³/hour metric (BWB-02) | ○ fact closure (RES-06) | ○ governorate coverage (PIPE-07) | ● loss-source breakdown (BWB-05, WEB-10) | ○ complete crew loop | ● Field-verified outcomes (LRN-06), pilot pack (DEMO-08) |
| Functionality & Practicality (20%) | ● offline end-to-end demo (OPS-03, WEB-05, MOB-01, LRN-01) | ○ persona endpoints (API-06) | ○ offline basemap (PIPE-08) | ○ twin view (WEB-10) | ● real-phone PWA (MOB-02, MOB-03) | ● utility install (OPS-05, OPS-06) |
| Technical Quality & Execution (15%) | ● DB invariants (DB-01), Quantity contract (API-02), tests (TEST-01 to TEST-04) | ● CI, reproduce, PostGIS (OPS-04, PIPE-06, DB-04) | ○ model metrics (TEST-07) | ○ full graph model (BWB-05) | ○ RLS (DB-05) | ○ deployment (OPS-05) |
| Innovation & Creativity (20%) | ● fusion case (L2-03), next-best (BWB-03), live learning (LRN-01) | — | ○ forecast (AIM-08) | ● GNN, NISAR, unknown segments (L3-02 to L3-04) | ● full Remember loop (LRN-04), active learning (LRN-05) | ○ learned weights from real outcomes |
| Open-Source AI Integration (15%) | ● bake-off and MODELS.md (AIM-01, AIM-02), tool-driving agent (AGT-02), crew extractor (AIM-04) | ○ expanded evals (TEST-06) | ● Prithvi, forecast (AIM-09, AIM-08) | ● GNN (L3-02) | ○ five agents (AGT-08) | — |
| Privacy & Responsible Design (5%) | ● labels (UX-02), role gates (SEC-02), no accusation (SEC-03), local-only (SEC-01), disclosure (DEMO-05) | ● RBAC matrix, offline guard, threat model (SEC-05, SEC-06) | ○ PII-validated imports (L1-06) | — | ● RLS, EXIF strip (DB-05, MOB-03) | ● data agreement, responsible-use policy (SEC-07) |
