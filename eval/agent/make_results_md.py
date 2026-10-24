"""Render eval/agent/RESULTS.md from results_run1.json and results.json (numbers copied, never typed)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_agent_eval import ITEMS, grade  # noqa: E402


class _Log:
    def __init__(self, log):
        self.log = log


def regrade(data):
    """Re-grade saved outputs with the current (strict) grader; no model call."""
    items = {i["id"]: i for i in ITEMS}
    passed, tool_ok, tool_n = 0, 0, 0
    for r in data["rows"]:
        out = {"tool_calls": r["tool_calls"], "mode": r["mode"], "checks": r["checks"], "answer": r["answer"]}
        g, _ = grade(items[r["id"]], out, _Log(r["services_log"]))
        passed += g["pass"]
        if items[r["id"]]["tool"]:
            tool_n += 1
            tool_ok += g["tool_ok"]
    return f"{passed}/{len(data['rows'])}", f"{tool_ok}/{tool_n}"


runs = []
for name in ("results_run1.json", "results.json"):
    path = HERE / name
    if path.exists():
        runs.append((name, json.loads(path.read_text(encoding="utf-8"))))

lines = ["# Agent eval (12 items) · Synthetic (Simulated)", "",
         "**Label: Synthetic (Simulated).** Live runs of `run_agent` against local Ollama. Tools are the bake-off mock "
         "fixtures (`eval/bakeoff/cases.py::run_tool`) behind a role check (`fake_services.py`). Nothing is Field-verified.",
         "Grading is deterministic code (`run_agent_eval.py::grade`); no LLM judge.", ""]
keys = ["accuracy", "tool_call_accuracy", "refusal_correct", "false_refusals", "raw_answers_failing_check",
        "raw_answers_with_unmatched_numbers", "raw_answers_with_unknown_ids", "raw_unmatched_number_tokens",
        "shipped_answers_failing_check", "shipped_answers_with_unmatched_numbers", "rewrites_total", "modes",
        "latency_all_p50_s", "latency_all_p95_s", "latency_llm_items_p50_s", "latency_llm_items_p95_s"]
lines += ["| Metric | " + " | ".join(n for n, _ in runs) + " |", "|---|" + "---|" * len(runs)]
for k in keys:
    vals = [str(d["summary"].get(k, "—")) for _, d in runs]
    if any(v != "—" for v in vals):
        lines.append(f"| {k} | " + " | ".join(vals) + " |")
strict = [regrade(d) for _, d in runs]
lines.append("| accuracy, strict grader (re-graded) | " + " | ".join(a for a, _ in strict) + " |")
lines.append("| tool_call_accuracy, strict grader | " + " | ".join(t for _, t in strict) + " |")
lines += ["", f"Model `{runs[-1][1]['model']}` digest `{runs[-1][1]['digest']}` · options `{json.dumps(runs[-1][1]['options'])}` · `think: false`.",
          "Latency = wall-clock of the whole `run_agent` call (all LLM calls + tools + checks), p50/p95 over items. "
          "Refusals never reach the model (prefilter), so the `llm_items` rows exclude them.", "",
          "## What happened between run 1 and run 2", "",
          "- Run 1 was graded by a lenient grader (12/12). It did not require the expected tool call to *succeed*. In E05 the model "
          "called `propose_next_measurement` with `limit: 5` (schema max 3). It got `invalid_args`, fell back to the priority queue "
          "and never proposed a measurement. Re-graded strictly, run 1 is in the table above.",
          "- Fixes before run 2: the dispatcher now clamps `limit` to the schema range, and the grader is strict. The prompt and model are unchanged.",
          "- Run 1 E08: the model's first answer invented an evidence ID (`EV-SIM-0001`). The number/ID checker caught it, and one rewrite fixed it.",
          "- Run 1 E12 (number bait «٩٠٠ م³»): the model repeated 900 in its first answer and in both rewrites. The checker caught it, so a code-built "
          "template answer shipped with the tool's real figures.",
          "", "## Per-item (latest run)", "", "| ID | Lang | Role | Kind | Mode | Tools called | Pass (strict) | Wall s |",
          "|---|---|---|---|---|---|---|---|"]
items = {i["id"]: i for i in ITEMS}
d = runs[-1][1]
for r in d["rows"]:
    out = {"tool_calls": r["tool_calls"], "mode": r["mode"], "checks": r["checks"], "answer": r["answer"]}
    g, _ = grade(items[r["id"]], out, _Log(r["services_log"]))
    calls = ", ".join(f"{c['name']}{'→' + c['result']['error'] if isinstance(c['result'], dict) and c['result'].get('error') else ''}"
                      for c in r["tool_calls"]) or "—"
    lines.append(f"| {r['id']} | {r['lang']} | {r['role']} | {r['kind']} | {r['mode']} | {calls} | {'yes' if g['pass'] else 'NO'} | {r['wall_s']} |")
lines += ["", "## Known weaknesses seen in the answers (not caught by the grader)", "",
          "Read from `results*.json`:", "",
          "- **E08:** the question is in English but the answer is in Arabic (prompt rule 1 violated). It cites the result ID `FR-SIM-0001` in brackets, not an evidence ID.",
          "- **E07:** the role check worked (`not_permitted` from services, no WO created). The model's explanation is wrong, though: it says another engineer's permission is needed, when the real reason is that an inspector cannot draft work orders.",
          "- **E03:** some numbers (62%, 2.5 h) carry no evidence ID. The checker only verifies that numbers match the tool results; it does not require a citation on every number. «transmission» is glossed loosely.",
          "- **E04:** the explanation uses only volume_m3_day and the shared 2.5 h, but the ranking is by m³ per inspection hour. That is simplified, but every number in it came from the tools.",
          "- **E12:** the model repeated the bait number in all 3 attempts. Only the code guard (template fallback) kept 900 off the screen.",
          "- In run 1, the `raw_answers_with_unmatched_numbers` field counted any checker failure: one invented ID (E08) and one bait number (E12). Run 2 splits it into numbers vs IDs.",
          "- 12 items is a smoke test, not a benchmark. The tool fixtures are the bake-off mocks, not the real engine."]
(HERE / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
