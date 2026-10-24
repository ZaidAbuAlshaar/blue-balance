"""Render eval/extract/RESULTS.md from results.json (numbers are copied, never typed by hand)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
s = d["summary"]
frozen = (HERE / "FROZEN.txt").read_text(encoding="utf-8").strip()
cols = [("LLM raw model output", "llm_raw_model_output"), ("LLM after span verify", "llm_after_span_verify"),
        ("LLM final (verify + guard)", "llm_final_after_guard"), ("Rules raw", "rules_raw"),
        ("Rules final (+ guard)", "rules_final_after_guard")]


def row(label, key, fmt=str):
    return f"| {label} | " + " | ".join(fmt(s[c][key]) for _, c in cols) + " |"


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


lines = [
    "# Extractor held-out eval: LLM vs rules · Synthetic (Simulated)",
    "",
    "**Label: Synthetic (Simulated).** 30 synthetic Jordanian-Arabic crew reports (H01–H30), written for this eval. "
    "None comes from a real inspection. Nothing here is Field-verified.",
    "",
    f"- Extractor model: `{d['model']}` · options `{json.dumps(d['options'])}` · `think: false`",
    "- Baseline: `bb/extract/rules.py` (lexicon + regex, offline, no model)",
    f"- Run: {d['started_utc']} → {d['finished_utc']} (UTC) · LLM errors: {s['llm_errors']}",
    "- Frozen set:",
    "",
    "```",
    frozen,
    "```",
    "",
    "## Results",
    "",
    "| Metric | " + " | ".join(c for c, _ in cols) + " |",
    "|---|" + "---|" * len(cols),
    row("Field accuracy", "field_accuracy", pct),
    row("Cells correct", "cells_correct"),
    row("Cells scored", "cells_scored"),
    row("Span exact-match (filled fields)", "span_exact_match", pct),
    row("Fields filled", "fields_filled"),
    row("Empty when unsupported", "empty_when_unsupported", pct),
    row("Unsupported cells", "cells_unsupported"),
    row("needs_confirmation cells", "needs_confirmation"),
    row("…of which gold value is among candidates", "needs_confirmation_gold_in_candidates"),
    "",
    f"- LLM raw span exact-match (before the verifier): {s['llm_raw_span_exact_match']}",
    f"- LLM latency (Ollama total_duration): median {s['llm_latency_median_s']} s, p95 {s['llm_latency_p95_s']} s; rules run in milliseconds.",
    f"- Gold lint issues (key not in report / bad enum): {s['gold_lint_issues'] or 'none'}",
    "",
    "### Per-field accuracy",
    "",
    "| Field | " + " | ".join(c for c, _ in cols) + " |",
    "|---|" + "---|" * len(cols),
]
for f in s["rules_raw"]["per_field_accuracy"]:
    lines.append(f"| {f} | " + " | ".join(s[c]["per_field_accuracy"][f] for _, c in cols) + " |")
lines += ["", "### Guard expectations (scored separately)", "", "| Report | Expectation | LLM | Rules |", "|---|---|---|---|"]
for a, b in zip(s["guard_expectations_llm"], s["guard_expectations_rules"]):
    lines.append(f"| {a['id']} | {a['expect']} | {'met' if a['met'] else 'NOT met'} | {'met' if b['met'] else 'NOT met'} |")
lines += [
    "",
    "## How to read this",
    "",
    "- **Field accuracy** uses the bake-off scorer (`score_cell`), with one change made before any run: the number parser maps «٫» to «.».",
    "- **LLM final** is what ships. The guard sets `needs_confirmation` (value blanked, candidates kept) when an enum field has cues for 2+ values, or when a span sits inside an instruction-like sentence. A blanked cell counts as wrong unless gold is empty, so the guard costs accuracy on purpose. The crew confirms in the UI.",
    "- **Empty when unsupported** = share of gold-empty cells that were left empty.",
    "- **Limits:** 30 reports, one author. The same AI builder wrote the reports, the gold and `rules.py`; the lexicon was drafted from the dev set C01–C10 before the held-out set was written, but the writer knew both, so this is **not a blinded** eval (A7 U1.4 asks for a teammate to write the set). Small sample: one cell ≈ " + f"{100 / s['llm_final_after_guard']['cells_scored']:.1f}" + " pp of field accuracy.",
]
lines += [
    "",
    "## Verdict",
    "",
    "- On this frozen set **the LLM does not beat the rules baseline**. Shipped field accuracy is LLM "
    f"{pct(s['llm_final_after_guard']['field_accuracy'])} vs rules {pct(s['rules_final_after_guard']['field_accuracy'])}; "
    f"raw it is {pct(s['llm_raw_model_output']['field_accuracy'])} vs {pct(s['rules_raw']['field_accuracy'])}. The rules are also better at leaving unsupported fields empty. "
    "Per field (shipped), the LLM wins on location and datetime, and the rules win on flow_or_size, water_use and observation_type (see the table above).",
    "- The guard caught both planted injections (H08, H09) and the genuine severity conflict (H22) for **both** methods.",
    "",
    "## Possible scorer / gold issues (reported, NOT fixed; the frozen set is unchanged)",
    "",
    "- **Scorer cannot read number words.** In H10 the LLM wrote «نص انش» (gold 0.5) and in H21 «عشرة كوب بالساعة» (gold 10). Both are "
    "arguably right, but `first_number` finds no digit, so they score wrong. rules.py converts these words to digits, so it is not penalised. Effect: about 2 cells against the LLM.",
    "- **Asset gold keys may be over-strict.** In H13, H24 and H30 the gold keys include the size («الخط 4 إنش», «الخط ٣ انش», «خط 2 انش»), while the LLM returned «الخط» / «خط». "
    "Whether the bare line counts is a judgment call. Effect: up to 3 cells against the LLM.",
    "- Even if all 5 of those cells were credited, the LLM's shipped accuracy would only roughly tie the rules. It would not clearly beat them.",
]
(HERE / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:40]))
