# Submission text (paste into the MLH "Submit a Project" form)

**Project name:** Blue Balance (ميزان الأزرق)

**Tagline:** Ranks where Jordan's water inspectors should go first: expected m³ of loss stopped per inspection hour, from satellite and pipeline signals, with open-weight AI running offline.

**Track:** Green Tech & Earth Preservation. Also applying to: Best Open-Source AI Project; Best Use of Gemma 4.

**What it does**
Jordan loses 41% of its water as non-revenue water (Petra, Aug 2026), and the ministry estimates about 70% of loss comes from attacks on lines and sources. Blue Balance ranks inspection candidates along the Desert Highway main line at Qatraneh, Karak:
- **Line signal:** a hydraulic twin (WNTR/EPANET) turns the meter imbalance on each segment into a likelihood. It is simulated, because real meter data is restricted.
- **Source signal:** Sentinel-2 dry-season NDVI from 2017 to 2026 finds new greenness near the line. This is real data. WorldCover checks whether it is inside existing farmland.
- **Fusion:** a Bayesian update fuses the two (0.71 line only, 0.82 fused for the top segment). The queue is ranked by expected m³/day stopped per inspection hour, always with intervals.
- **Learning:** field results update the posteriors live.
- **AI:** a local Qwen3.5-4B agent answers Arabic questions through tools, and a local Gemma 4 E4B extractor turns Jordanian-Arabic crew reports into 10 fields, each tied to its exact words.
- **Remember:** a crew-verified finding becomes a draft map edit that a second engineer must approve. None exist yet; today's demo entries are Simulated.

**How we built it**
- FastAPI + SQLite, where the database enforces the evidence labels, intervals, append-only history and approver ≠ proposer.
- A NumPy/SciPy Bayesian engine with WNTR 1.5.
- Sentinel-2/WorldCover/DEM via the Planetary Computer STAC, ERA5 via Open-Meteo, and the OSM route.
- Ollama with qwen3.5:4b and gemma4:e4b-it-qat (both Apache-2.0), chosen by a measured bake-off.
- Vite + React + TypeScript + MapLibre, Arabic-first RTL.

**Challenges**
- **Agent choice:** Gemma 4 E4B was the better extractor (95.9% on the dev set) but the weaker agent. It asked permission instead of calling tools and invented case IDs, so we split the roles by measured results.
- **Prompt injection:** Gemma obeyed an injected instruction inside a crew report, so we added a code-level guard.
- **Data gaps:** the 2021 and 2024 Sentinel-2 scenes were corrupt or empty, so we replaced them.
- **No isolated fields:** all 14 candidates turned out to sit inside existing farmland. We kept that honest instead of tuning thresholds, and we don't publish their exact locations in the repo.

**What we're proud of**
- Every number has an interval and an Observed / Simulated / Hypothesis / Field-verified label, enforced by the database.
- The agent cannot approve anything.
- We report the results that didn't go our way: LLM vs rules extractor is on par (90.9% vs 92.3%) on our held-out set.

**What's next**
- Real meter data from the utility, so the line signal becomes Observed.
- A blinded extractor test written by field crews.
- NISAR L-band for subsurface leaks.
- Prithvi-EO fine-tuning for field detection.
- A GNN over the distribution twin.

**Prior-work disclosure:** team members explored water loss before this event in the public repos kurdim12/missing-blue and aboodhaymouni/missing-blue (AI Quest 2026) and ZaidAbuAlshaar/mizan (AstroCode 2026). No code, data or assets were reused. Blue Balance was written, and its data fetched, on 24 Oct 2026.

**Repo:** https://github.com/ZaidAbuAlshaar/blue-balance
