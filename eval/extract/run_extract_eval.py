"""Held-out extractor eval: Gemma (LLM) vs the rule-based baseline on the FROZEN 30-report set.

Usage (from backend/):  set PYTHONUTF8=1 && python ../eval/extract/run_extract_eval.py
Refuses to run if heldout.json no longer matches the SHA-256 in FROZEN.txt.
All reports are Synthetic (Simulated). Writes eval/extract/results.json and prints a summary.

Scoring = the bake-off scorer (eval/bakeoff/run_bakeoff.py::score_cell) with one change made BEFORE any run:
the number parser also maps the Arabic decimal separator «٫» to "." (the bake-off parser read «٦٫٥» as 6).
"""
import hashlib
import json
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from bb import config  # noqa: E402
from bb.extract import guard, rules, verify  # noqa: E402
from bb.extract.extractor import call_llm  # noqa: E402
from bb.extract.schema import ENUMS, FIELDS  # noqa: E402

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫", "01234567890123456789.")
STRIP = re.compile("[ً-ْـ‎‏؜‪-‮⁦-⁩]")


def norm(text):
    text = unicodedata.normalize("NFKC", text).translate(AR_DIGITS)
    text = STRIP.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def first_number(text):
    match = re.search(r"\d+(?:[.,]\d+)?", norm(text))
    return float(match.group().replace(",", ".")) if match else None


def score_cell(spec, cell):
    value = cell.get("value") if isinstance(cell, dict) else None
    if isinstance(value, str) and not value.strip():
        value = None
    kind = spec[0]
    if kind == "skip":
        return None
    if kind == "null":
        return value is None
    if kind == "exact":
        if value is None:
            return None in spec[1]
        return any(a is not None and norm(str(value)).replace(" ", "") == norm(a).replace(" ", "") for a in spec[1])
    if kind == "num":
        number = first_number(str(value)) if value is not None else None
        return number is not None and abs(number - spec[1]) < 1e-6
    if kind == "key":
        span = cell.get("span") or ""
        return value is not None and norm(spec[1]) in norm(f"{value} {span}")
    raise ValueError(kind)


def unsupported(spec):
    return spec[0] == "null" or (spec[0] == "exact" and spec[1] == [None])


def gold_lint(reports):
    """Report (never fix) gold problems: key substrings that are not in the report, bad enum values."""
    issues = []
    for r in reports:
        for field, spec in r["gold"].items():
            if spec[0] == "key" and norm(spec[1]) not in norm(r["text"]):
                issues.append(f"{r['id']}.{field}: key {spec[1]!r} not in report")
            if spec[0] == "exact" and field in ENUMS:
                bad = [v for v in spec[1] if v is not None and v not in ENUMS[field]]
                if bad:
                    issues.append(f"{r['id']}.{field}: values {bad} not in enum")
    return issues


def summarize(rows, key):
    correct = scored = filled = span_ok = unsup = empty_ok = nc = nc_gold_in = 0
    per_field = {f: [0, 0] for f in FIELDS}
    for row in rows:
        fields = row[key]
        for field in FIELDS:
            spec = row["gold"][field]
            cell = fields.get(field) or {}
            result = score_cell(spec, cell)
            if result is not None:
                scored += 1
                correct += bool(result)
                per_field[field][0] += bool(result)
                per_field[field][1] += 1
            if unsupported(spec):
                unsup += 1
                empty_ok += cell.get("value") in (None, "")
            if cell.get("value") not in (None, ""):
                filled += 1
                span = cell.get("span")
                span_ok += bool(span) and span in row["text"]
            if cell.get("status") == "needs_confirmation":
                nc += 1
                if spec[0] == "exact":
                    nc_gold_in += any(c["value"] in spec[1] for c in cell.get("candidates", []))
    return {
        "field_accuracy": round(correct / scored, 3) if scored else None, "cells_correct": correct, "cells_scored": scored,
        "span_exact_match": round(span_ok / filled, 3) if filled else None, "fields_filled": filled,
        "empty_when_unsupported": round(empty_ok / unsup, 3) if unsup else None, "cells_unsupported": unsup,
        "needs_confirmation": nc, "needs_confirmation_gold_in_candidates": nc_gold_in,
        "per_field_accuracy": {f: f"{c}/{n}" for f, (c, n) in per_field.items()},
    }


def guarded(text, fields):
    flags = guard.instruction_flags(text)
    out = guard.apply(text, json.loads(json.dumps(fields)), flags)
    return out, flags


def main():
    data_bytes = (HERE / "heldout.json").read_bytes()
    digest = hashlib.sha256(data_bytes).hexdigest()
    frozen = (HERE / "FROZEN.txt").read_text(encoding="utf-8")
    if digest not in frozen:
        sys.exit(f"heldout.json changed after freezing: {digest}")
    data = json.loads(data_bytes.decode("utf-8"))
    reports = data["reports"]
    lint = gold_lint(reports)
    rows = []
    started = datetime.now(timezone.utc).isoformat()
    for r in reports:
        text = r["text"]
        row = {"id": r["id"], "text": text, "gold": r["gold"], "expect": r.get("expect", {})}
        rules_raw = rules.extract_rules(text)
        row["rules_raw"] = rules_raw
        row["rules_final"], row["rules_flags"] = guarded(text, rules_raw)
        try:
            raw, timing = call_llm(text)
            row["llm_raw_output"] = raw
            row["llm_timing"] = timing
            vflags = []
            row["llm_verified"] = verify.verify_fields(text, raw, vflags)
            row["llm_final"], gflags = guarded(text, row["llm_verified"])
            row["llm_flags"] = vflags + gflags
            # raw span exact-match, before the verifier touches anything
            filled = [(f, c) for f, c in raw.items() if isinstance(c, dict) and c.get("value") not in (None, "")]
            row["llm_raw_spans"] = [bool(c.get("span")) and c["span"] in text for _, c in filled]
            row["llm_raw_as_cells"] = {f: (c if isinstance(c, dict) else {}) for f, c in raw.items()}
        except Exception as exc:  # recorded, not hidden
            row["llm_error"] = repr(exc)
            row["llm_verified"] = row["llm_final"] = row["llm_raw_as_cells"] = {}
            row["llm_flags"], row["llm_raw_spans"], row["llm_timing"] = [], [], {}
        print(r["id"], row.get("llm_timing", {}).get("total_s"), row.get("llm_error", ""), flush=True)
        rows.append(row)

    def expect_report(key_fields, key_flags):
        out = []
        for row in rows:
            exp = row["expect"]
            for flag in exp.get("flags", []):
                out.append({"id": row["id"], "expect": flag, "met": flag in row[key_flags]})
            for field in exp.get("needs_confirmation", []):
                out.append({"id": row["id"], "expect": f"needs_confirmation:{field}",
                            "met": row[key_fields][field].get("status") == "needs_confirmation"})
        return out

    raw_spans = [ok for row in rows for ok in row["llm_raw_spans"]]
    times = [row["llm_timing"].get("total_s") for row in rows if row["llm_timing"].get("total_s")]
    summary = {
        "reports": len(rows), "heldout_sha256": digest, "gold_lint_issues": lint,
        "llm_errors": sum("llm_error" in row for row in rows),
        "llm_raw_model_output": summarize(rows, "llm_raw_as_cells"),
        "llm_after_span_verify": summarize(rows, "llm_verified"),
        "llm_final_after_guard": summarize(rows, "llm_final"),
        "rules_raw": summarize(rows, "rules_raw"),
        "rules_final_after_guard": summarize(rows, "rules_final"),
        "llm_raw_span_exact_match": f"{sum(raw_spans)}/{len(raw_spans)}",
        "guard_expectations_llm": expect_report("llm_final", "llm_flags"),
        "guard_expectations_rules": expect_report("rules_final", "rules_flags"),
        "llm_latency_median_s": round(statistics.median(times), 2) if times else None,
        "llm_latency_p95_s": round(sorted(times)[int(0.95 * (len(times) - 1))], 2) if times else None,
    }
    out = {"label": "Synthetic (Simulated)", "model": config.EXTRACT_MODEL, "options": config.LLM_OPTIONS,
           "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(), "summary": summary,
           "rows": rows}
    (HERE / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
