# Extractor held-out eval: LLM vs rules · Synthetic (Simulated)

**Label: Synthetic (Simulated).** 30 synthetic Jordanian-Arabic crew reports (H01–H30), written for this eval. None comes from a real inspection. Nothing here is Field-verified.

- Extractor model: `gemma4:e4b-it-qat` · options `{"temperature": 0, "seed": 42, "num_ctx": 8192}` · `think: false`
- Baseline: `bb/extract/rules.py` (lexicon + regex, offline, no model)
- Run: 2026-10-24T13:15:27.523862+00:00 → 2026-10-24T13:17:31.538207+00:00 (UTC) · LLM errors: 0
- Frozen set:

```
heldout.json SHA-256: 11bce840bb06b2e1dd700ca6ec3cfea8ed2b028183f918b992f4b42367adfb14
Frozen at: 2026-10-24T16:07:08+03:00
Frozen BEFORE any extractor model run and before rules.py was written.
Label: Synthetic (Simulated). 30 reports H01-H30.
```

## Results

| Metric | LLM raw model output | LLM after span verify | LLM final (verify + guard) | Rules raw | Rules final (+ guard) |
|---|---|---|---|---|---|
| Field accuracy | 92.7% | 92.3% | 90.9% | 94.1% | 92.3% |
| Cells correct | 266 | 265 | 261 | 270 | 265 |
| Cells scored | 287 | 287 | 287 | 287 | 287 |
| Span exact-match (filled fields) | 97.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| Fields filled | 212 | 207 | 200 | 205 | 198 |
| Empty when unsupported | 93.8% | 95.0% | 95.0% | 96.3% | 96.3% |
| Unsupported cells | 80 | 80 | 80 | 80 | 80 |
| needs_confirmation cells | 0 | 0 | 7 | 0 | 7 |
| …of which gold value is among candidates | 0 | 0 | 6 | 0 | 6 |

- LLM raw span exact-match (before the verifier): 206/212
- LLM latency (Ollama total_duration): median 3.82 s, p95 4.24 s; rules run in milliseconds.
- Gold lint issues (key not in report / bad enum): none

### Per-field accuracy

| Field | LLM raw model output | LLM after span verify | LLM final (verify + guard) | Rules raw | Rules final (+ guard) |
|---|---|---|---|---|---|
| site_id | 30/30 | 30/30 | 30/30 | 30/30 | 30/30 |
| location | 27/28 | 27/28 | 27/28 | 24/28 | 24/28 |
| nearest_asset | 22/27 | 22/27 | 22/27 | 22/27 | 22/27 |
| observation_type | 29/30 | 28/30 | 24/30 | 30/30 | 25/30 |
| water_use | 27/30 | 27/30 | 27/30 | 30/30 | 30/30 |
| flow_or_size | 22/30 | 22/30 | 22/30 | 27/30 | 27/30 |
| evidence_attached | 29/30 | 29/30 | 29/30 | 29/30 | 29/30 |
| severity | 27/29 | 28/29 | 28/29 | 28/29 | 28/29 |
| datetime | 30/30 | 30/30 | 30/30 | 28/30 | 28/30 |
| notes_action | 23/23 | 22/23 | 22/23 | 22/23 | 22/23 |

### Guard expectations (scored separately)

| Report | Expectation | LLM | Rules |
|---|---|---|---|
| H08 | possible_injection | met | met |
| H09 | possible_injection | met | met |
| H22 | needs_confirmation:severity | met | met |

## How to read this

- **Field accuracy** uses the bake-off scorer (`score_cell`), with one change made before any run: the number parser maps «٫» to «.».
- **LLM final** is what ships. The guard sets `needs_confirmation` (value blanked, candidates kept) when an enum field has cues for 2+ values, or when a span sits inside an instruction-like sentence. A blanked cell counts as wrong unless gold is empty, so the guard costs accuracy on purpose. The crew confirms in the UI.
- **Empty when unsupported** = share of gold-empty cells that were left empty.
- **Limits:** 30 reports, one author. The same AI builder wrote the reports, the gold and `rules.py`; the lexicon was drafted from the dev set C01–C10 before the held-out set was written, but the writer knew both, so this is **not a blinded** eval (A7 U1.4 asks for a teammate to write the set). Small sample: one cell ≈ 0.3 pp of field accuracy.

## Verdict

- On this frozen set **the LLM does not beat the rules baseline**. Shipped field accuracy is LLM 90.9% vs rules 92.3%; raw it is 92.7% vs 94.1%. The rules are also better at leaving unsupported fields empty. Per field (shipped), the LLM wins on location and datetime, and the rules win on flow_or_size, water_use and observation_type (see the table above).
- The guard caught both planted injections (H08, H09) and the genuine severity conflict (H22) for **both** methods.

## Possible scorer / gold issues (reported, NOT fixed; the frozen set is unchanged)

- **Scorer cannot read number words.** In H10 the LLM wrote «نص انش» (gold 0.5) and in H21 «عشرة كوب بالساعة» (gold 10). Both are arguably right, but `first_number` finds no digit, so they score wrong. rules.py converts these words to digits, so it is not penalised. Effect: about 2 cells against the LLM.
- **Asset gold keys may be over-strict.** In H13, H24 and H30 the gold keys include the size («الخط 4 إنش», «الخط ٣ انش», «خط 2 انش»), while the LLM returned «الخط» / «خط». Whether the bare line counts is a judgment call. Effect: up to 3 cells against the LLM.
- Even if all 5 of those cells were credited, the LLM's shipped accuracy would only roughly tie the rules. It would not clearly beat them.
