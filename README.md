# Blue Balance · ميزان الأزرق

**Blue Balance ranks where water inspectors in Karak, Jordan should go first.** It ranks candidates by the expected cubic metres of loss stopped per hour of inspection. It runs offline on one laptop, with open-weight AI only.

> Detect · Verify · Remember: the satellite detects, the crew verifies, the map remembers.

Built at **Hacktoberfest Hack Day Amman × JOSA, 24 Oct 2026**, by team VCoders. Track: **Green Tech & Earth Preservation**. Every lost cubic metre was pumped, often uphill, so stopping loss also saves electricity and CO₂.

---

## Why
- Jordan's non-revenue water is **41%** ([Petra, Aug 2026](https://petra.gov.jo/index.php/en/news/water-loss-cut-to-41-exceeding-target)). A ministry statement gives **42.3%** ([Al-Mamlaka, 20 Aug 2026](https://www.almamlakatv.com/news/207766-)), so we show both.
- The ministry counted **133,408** attacks on main and transmission lines from June 2013 to June 2026. It estimates attacks on lines and sources at **about 70%** of water loss. That is a ministry estimate, not an audited water balance ([Al-Mamlaka, 20 Aug 2026](https://www.almamlakatv.com/news/207766-)).
- Illegal connections have been dismantled in the Qatraneh area on the desert line ([Petra](https://petra.gov.jo/en/news/illegal-water-connections-dismantled-in-qatraneh-area-waj)). That is our pilot corridor.

## What it does (today's build)
| Step | What happens | Label |
|---|---|---|
| **Detect: line** | A WNTR/EPANET twin of the main-line segments along the Desert Highway compares the inflow and outflow meters. A tap shows up as a flow imbalance. | Simulated |
| **Detect: source** | Dry-season Sentinel-2 NDVI change, 2017 → 2026, finds new greenness near the line. ESA WorldCover checks whether it sits inside existing cropland. | Observed |
| **Fuse** | A Bayesian update combines the two independent signals. For segment KRK-T-002, the posterior is 0.71 from the line alone, 0.11 from the field alone, and **0.82 fused**, each with a 90% interval. | Hypothesis |
| **Rank** | Expected m³/day stopped ÷ (travel + inspection hours), with intervals. The next-best measurement is chosen by expected information gain per hour. | Hypothesis |
| **Verify** | The crew enters a result ("found / not found"). The posterior updates by Bayes and the queue re-ranks live. Crew reports in Jordanian Arabic become 10 fields, each tied to the exact words it came from. | Simulated demo entries |
| **Remember** | A crew-verified finding becomes a **draft** map edit. None exist yet; today's demo entries are Simulated. A *different* engineer approves it, and it exports as GeoJSON in EPSG:4326 / 28191 / 3066. | Hypothesis |
| **Ask** | An Arabic agent answers questions by calling tools over the engine. Every number is checked against the tool results before it is shown. | Hypothesis |

## Open-weight AI
Both models run locally in Ollama on an RTX 4060 Laptop (8 GB), and both are Apache-2.0. We chose them with a measured bake-off; see [MODELS.md](MODELS.md).

| Role | Model | Evidence (synthetic test data) |
|---|---|---|
| Agent (Arabic tool calling) | `qwen3.5:4b` | Bake-off tool calls: 9/10 with the first prompt (Gemma 4 E4B: 2/10), and 10/10 (Gemma: 7/10) with a second prompt written after seeing round-1 failures. 3/3 refusals. Live agent eval: 12/12, and 0/12 shipped answers failed the number check ([eval/agent](eval/agent/RESULTS.md)). |
| Crew-report extractor | `gemma4:e4b-it-qat` | Dev set: 95.9% field accuracy. On a frozen 30-report held-out set it was **on par with our rule-based extractor**: 90.9% vs 92.3%. That set was not blinded ([eval/extract](eval/extract/RESULTS.md)). |

Guardrails are in code, not in the prompt:
- the number and ID checker, with rewrite and template fallback
- exact-span verification for every extracted field
- an injection and conflicting-cue guard, which caught 2/2 planted injections
- a refusal prefilter for accusations and personal data
- no approve tool, so the agent can only draft

## Honesty and privacy (enforced by the database)
- **Labels are a closed set.** Every number carries `Observed`, `Simulated`, `Hypothesis` or `Field-verified`, plus a 90% interval. SQLite CHECK constraints reject anything else.
- **Nothing is Field-verified today.**
- **Append-only history.** Evidence and posteriors cannot be edited, and the audit log is a SHA-256 hash chain.
- **Separation of duties.** A work order or map edit cannot be approved by the person who proposed it, and never by the agent.
- **No personal data.** There are no owner names; sites have internal IDs only. Inspectors and engineers see case locations, and every view is logged. Admins see the audit log, not the map.
- **Local only.** Models and server bind to `127.0.0.1`, with no external telemetry.
- **A candidate is not a violation.** The UI and the agent never say "theft".

## Limits (we say them first)
- **The main-line route is approximate.** It follows the Desert Highway, taken from OpenStreetMap, because the real pipeline geometry is restricted. The line meters and the tap are **simulated**; no SCADA data was used.
- **All 14 Sentinel-2 candidates sit inside existing cropland**, so crop rotation is the likely cause. Twelve are within about 1.2 km of the route and two are about 15 km away. Their isolation feature is 0, so on its own the field signal is weak: 0.11 for KRK-F-001. It adds only modestly when fused with the line signal (0.71 → 0.82). We did not find an isolated new desert field in this area.
- **Exact candidate geometries and image chips are not published here.** They show real farm plots, and listing them publicly as "candidates" could stigmatise farmers. They are regenerated locally from public Sentinel-2 data by the pipeline below.
- **Priors, likelihood calibration, crop coefficients, travel speed, lift and pump efficiency are ASSUMED.** Each one is stored as evidence and shown on the transparency screen.
- **Crew reports are synthetic, and the eval sets are small and synthetic.**
- **Satellites see surface water use only.** Subsurface leaks need L-band radar (NISAR), which is not in today's build.

## Run it (offline)
Requirements:
- Windows
- Python 3.11 with `pip install -r requirements.txt`
- Node 22 + pnpm
- [Ollama](https://github.com/ollama/ollama) with `qwen3.5:4b` and `gemma4:e4b-it-qat` pulled

Paths:
- The data root defaults to `E:\blue-balance-data`; set `BB_DATA_ROOT` to change it, and `BB_DB` for the database file.
- `ops\start.ps1` expects Ollama at `E:\ollama\bin\ollama.exe` with its models in `E:\ollama\models`. Edit the two paths at the top of the script if yours differ.

1. **Rebuild the data** (once, needs internet; the raw imagery is about 0.3 GB):
   ```powershell
   set PYTHONUTF8=1
   python pipeline\fetch_raw.py
   python pipeline\refetch_year.py 2021 2024   # replaces the corrupt 2021 and empty 2024 scenes
   python pipeline\make_route.py
   python pipeline\process_fields.py
   cd backend; python -m bb.engine.precompute; cd ..
   ```
2. **Build the web app and start everything** (works offline from here):
   ```powershell
   cd web; pnpm install; pnpm build; cd ..
   powershell -ExecutionPolicy Bypass -File ops\start.ps1
   ```
   `start.ps1` starts Ollama on 127.0.0.1, preloads both models, seeds the database if it is missing and serves the app at http://127.0.0.1:8000. Demo accounts are written to `data/synthetic/demo_users.json`, which is not committed.

**Tests:** run `cd backend; python -m pytest -m "not llm"`. That covers database rules, services, API, engine, data, agent and extractor. Run `python -m pytest` to include the live-LLM tests.

## Repository
```
backend/bb/   db (rules), services (roles + audit), engine (twin, fusion, priority, learning, next-best, energy),
              agent (tool loop, number checker, refusals), extract (LLM + rules + span verifier + guard), api
pipeline/     raw data fetch and Sentinel-2 processing
data/         processed outputs (Observed / Simulated) and synthetic demo data
eval/         LLM bake-off, agent eval, extractor held-out eval
web/          Vite + React + TypeScript + MapLibre, Arabic-first RTL
docs/         module contracts
TECH_STACK.md · MODELS.md · CHECKLIST.md (roadmap) · DEMO.md · SUBMISSION.md   (repo root)
```

## Data and licences
Data sources:
- **Copernicus Sentinel-2 L2A** via Microsoft Planetary Computer
- **ESA WorldCover 2021** (CC BY 4.0)
- **Copernicus DEM GLO-30**
- **ERA5** via Open-Meteo (CC BY 4.0)
- **Route:** © OpenStreetMap contributors (ODbL)

Software: WNTR (Revised BSD), EPANET 2.2 (MIT). Models: Qwen3.5 and Gemma 4 (Apache-2.0).

This project is licensed under the Apache License 2.0 (see `LICENSE`).

## Prior-work disclosure
Members of the team explored water loss before this event, in the public repositories `kurdim12/missing-blue` and `aboodhaymouni/missing-blue` (AI Quest 2026) and `ZaidAbuAlshaar/mizan` (AstroCode 2026). **No code, data or assets from them were reused.** Blue Balance was written, and its data fetched, on 24 October 2026; the git history starts that day.
