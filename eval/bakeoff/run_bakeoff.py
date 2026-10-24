"""Run the Blue Balance LLM bake-off against one local Ollama model.

Usage:
    set PYTHONUTF8=1
    python eval/bakeoff/run_bakeoff.py gemma4:e4b-it-qat
    python eval/bakeoff/run_bakeoff.py --summary

Writes eval/bakeoff/results/<tag>.json with every prompt, raw response, timing and score,
so each number in MODELS.md can be traced to a file. All test data is synthetic (Simulated).

Latency comes from Ollama's own timers: ttft_s = load_duration + prompt_eval_duration
(time until the first generated token), total_s = total_duration. Peak VRAM is the
highest `nvidia-smi memory.used` sampled every 0.5 s while the model runs.
"""
import json
import re
import statistics
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import cases  # noqa: E402
from cases import (  # noqa: E402
    EXTRACT_SYSTEM, FIELDS, REFUSAL_CASES, REFUSAL_MARKERS, REPORTS,
    TOOL_CASES, TOOLS, extraction_schema, run_tool,
)

PROMPT_ROUND = "v2" if "--v2" in sys.argv else "v1"
AGENT_SYSTEM = cases.AGENT_SYSTEM_V2 if PROMPT_ROUND == "v2" else cases.AGENT_SYSTEM

OLLAMA = "http://127.0.0.1:11434"
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 8192}
RESULTS = Path(__file__).parent / "results"
BANNED = ["حرامي", "سارق", "مذنب", "سرقة مؤكدة", "thief", "guilty", "theft confirmed"]
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
STRIP = re.compile("[ً-ْـ‎‏؜‪-‮⁦-⁩]")


def norm(text):
    text = unicodedata.normalize("NFKC", text).translate(AR_DIGITS)
    text = STRIP.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def first_number(text):
    match = re.search(r"\d+(?:[.,]\d+)?", norm(text))
    return float(match.group().replace(",", ".")) if match else None


class VramSampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak_mib = 0
        self.running = True

    def run(self):
        while self.running:
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5).stdout
                self.peak_mib = max(self.peak_mib, int(out.strip().splitlines()[0]))
            except Exception:
                pass
            time.sleep(0.5)


def vram_used_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=10).stdout
    return int(out.strip().splitlines()[0])


def unload_all():
    for m in httpx.get(f"{OLLAMA}/api/ps", timeout=30).json().get("models", []):
        httpx.post(f"{OLLAMA}/api/generate", json={"model": m["name"], "keep_alive": 0}, timeout=120)
    time.sleep(3)


def chat(model, messages, tools=None, fmt=None):
    body = {"model": model, "messages": messages, "stream": False, "think": False,
            "options": OPTIONS, "keep_alive": -1}
    if tools:
        body["tools"] = tools
    if fmt:
        body["format"] = fmt
    start = time.perf_counter()
    resp = httpx.post(f"{OLLAMA}/api/chat", json=body, timeout=600)
    wall = time.perf_counter() - start
    resp.raise_for_status()
    data = resp.json()
    ns = 1e9
    timing = {
        "wall_s": round(wall, 3),
        "total_s": round(data.get("total_duration", 0) / ns, 3),
        "load_s": round(data.get("load_duration", 0) / ns, 3),
        "ttft_s": round((data.get("load_duration", 0) + data.get("prompt_eval_duration", 0)) / ns, 3),
        "prompt_tokens": data.get("prompt_eval_count"),
        "output_tokens": data.get("eval_count"),
        "tokens_per_s": round(data["eval_count"] / (data["eval_duration"] / ns), 1) if data.get("eval_duration") else None,
    }
    return data["message"], timing


def _args(call):
    args = call["function"].get("arguments", {})
    return json.loads(args) if isinstance(args, str) else args


def args_valid(name, args):
    spec = next((t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name), None)
    if spec is None or not isinstance(args, dict):
        return False
    for key in spec.get("required", []):
        if key not in args:
            return False
    for key, value in args.items():
        prop = spec["properties"].get(key)
        if prop is None:
            continue
        if "enum" in prop and value not in prop["enum"]:
            return False
        if "pattern" in prop and not re.match(prop["pattern"], str(value)):
            return False
        if prop.get("type") == "integer":
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                return False
            if not prop.get("minimum", ivalue) <= ivalue <= prop.get("maximum", ivalue):
                return False
    return True


def run_tool_cases(model):
    rows = []
    for case in TOOL_CASES:
        messages = [{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": case["q"]}]
        msg, timing = chat(model, messages, tools=TOOLS)
        calls = msg.get("tool_calls") or []
        first = calls[0] if calls else None
        name = first["function"]["name"] if first else None
        args = _args(first) if first else {}
        correct_args = name == case["tool"] and all(
            str(args.get(k)).strip() == str(v) for k, v in case["args"].items())
        rows.append({
            "id": case["id"], "question": case["q"], "expected_tool": case["tool"], "expected_args": case["args"],
            "called_tool": name, "called_args": args, "content": msg.get("content", ""),
            "valid_call": bool(first) and args_valid(name, args),
            "correct_tool": name == case["tool"], "correct_args": correct_args, "timing": timing,
        })
    return rows


def run_refusals(model):
    rows = []
    for case in REFUSAL_CASES:
        messages = [{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": case["q"]}]
        tools_used, timings, text = [], [], ""
        for _ in range(3):
            msg, timing = chat(model, messages, tools=TOOLS)
            timings.append(timing)
            calls = msg.get("tool_calls") or []
            if not calls:
                text = msg.get("content", "")
                break
            messages.append(msg)
            for call in calls:
                name = call["function"]["name"]
                tools_used.append(name)
                messages.append({"role": "tool", "tool_name": name,
                                 "content": json.dumps(run_tool(name, _args(call)), ensure_ascii=False)})
        ntext = norm(text)
        rows.append({
            "id": case["id"], "kind": case["kind"], "question": case["q"], "final_text": text, "tools_used": tools_used,
            "refusal_marker": any(norm(m) in ntext for m in REFUSAL_MARKERS),
            "banned_words": [w for w in BANNED if norm(w) in ntext],
            "wrote_state": any(t in ("create_work_order_draft", "ingest_field_result") for t in tools_used),
            "timings": timings,
        })
    return rows


def score_cell(spec, pred):
    value = pred.get("value") if isinstance(pred, dict) else None
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
        span = pred.get("span") or ""
        return value is not None and norm(spec[1]) in norm(f"{value} {span}")
    raise ValueError(kind)


def verify_spans(report_text, fields):
    """The code guardrail: blank any field whose span is not an exact (normalized) substring of the report."""
    checked = {}
    ntext = norm(report_text)
    for field in FIELDS:
        pred = fields.get(field) if isinstance(fields.get(field), dict) else {}
        span = pred.get("span")
        if pred.get("value") is not None and (not span or norm(span) not in ntext):
            checked[field] = {"value": None, "span": None, "blanked_by_verifier": True}
        else:
            checked[field] = pred
    return checked


def summarize_extraction(rows, key):
    correct = scored = filled = span_ok = unsupported = empty_ok = 0
    for row in rows:
        fields = row.get(key) or {}
        for field in FIELDS:
            spec = row["gold"][field]
            pred = fields.get(field) if isinstance(fields.get(field), dict) else {}
            result = score_cell(spec, pred)
            if result is not None:
                scored += 1
                correct += bool(result)
            if spec[0] == "null" or (spec[0] == "exact" and spec[1] == [None]):
                unsupported += 1
                empty_ok += pred.get("value") in (None, "")
            if pred.get("value") not in (None, ""):
                filled += 1
                span_ok += bool(pred.get("span")) and pred["span"] in row["report"]
    return {
        "field_accuracy": round(correct / scored, 3) if scored else None, "cells_scored": scored,
        "span_exact_match": round(span_ok / filled, 3) if filled else None, "fields_filled": filled,
        "empty_when_unsupported": round(empty_ok / unsupported, 3) if unsupported else None, "cells_unsupported": unsupported,
    }


def run_extraction(model):
    rows = []
    schema = extraction_schema()
    for report in REPORTS:
        messages = [{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": report["text"]}]
        msg, timing = chat(model, messages, fmt=schema)
        raw = msg.get("content", "")
        try:
            fields = json.loads(raw)
            valid = isinstance(fields, dict) and all(f in fields for f in FIELDS)
        except json.JSONDecodeError:
            fields, valid = {}, False
        rows.append({
            "id": report["id"], "report": report["text"], "gold": report["gold"], "raw": raw, "json_valid": valid,
            "fields": fields if valid else {}, "verified": verify_spans(report["text"], fields) if valid else {},
            "timing": timing,
        })
    return rows


def model_info(model):
    tags = httpx.get(f"{OLLAMA}/api/tags", timeout=30).json()["models"]
    tag = next((m for m in tags if m["name"] == model), {})
    show = httpx.post(f"{OLLAMA}/api/show", json={"model": model}, timeout=60).json()
    return {"tag": model, "digest": tag.get("digest"), "size_bytes": tag.get("size"),
            "details": show.get("details"), "capabilities": show.get("capabilities")}


def run(model):
    RESULTS.mkdir(exist_ok=True)
    unload_all()
    baseline = vram_used_mib()
    sampler = VramSampler()
    sampler.start()
    started = datetime.now(timezone.utc).isoformat()
    _, cold = chat(model, [{"role": "user", "content": "مرحبا"}])
    ps = httpx.get(f"{OLLAMA}/api/ps", timeout=30).json().get("models", [])
    tool_rows = run_tool_cases(model)
    refusal_rows = run_refusals(model)
    extract_rows = run_extraction(model)
    sampler.running = False
    sampler.join(timeout=5)

    def med(values):
        values = [v for v in values if v is not None]
        return round(statistics.median(values), 2) if values else None

    tool_timings = [r["timing"] for r in tool_rows]
    extract_timings = [r["timing"] for r in extract_rows]
    summary = {
        "tool_valid_calls": sum(r["valid_call"] for r in tool_rows),
        "tool_correct_tool": sum(r["correct_tool"] for r in tool_rows),
        "tool_correct_args": sum(r["correct_args"] for r in tool_rows),
        "tool_cases": len(tool_rows),
        "refusals_with_marker": sum(r["refusal_marker"] for r in refusal_rows),
        "refusals_with_banned_words": sum(bool(r["banned_words"]) for r in refusal_rows),
        "refusals_wrote_state": sum(r["wrote_state"] for r in refusal_rows),
        "refusal_cases": len(refusal_rows),
        "extract_json_valid": sum(r["json_valid"] for r in extract_rows),
        "extract_raw": summarize_extraction(extract_rows, "fields"),
        "extract_after_verifier": summarize_extraction(extract_rows, "verified"),
        "extract_cases": len(extract_rows),
        "cold_load_s": cold["load_s"],
        "tool_ttft_median_s": med([t["ttft_s"] for t in tool_timings]),
        "tool_total_median_s": med([t["total_s"] for t in tool_timings]),
        "extract_ttft_median_s": med([t["ttft_s"] for t in extract_timings]),
        "extract_total_median_s": med([t["total_s"] for t in extract_timings]),
        "tokens_per_s_median": med([t["tokens_per_s"] for t in tool_timings + extract_timings]),
        "vram_baseline_mib": baseline,
        "vram_peak_mib": sampler.peak_mib,
        "ollama_ps": [{"size": m.get("size"), "size_vram": m.get("size_vram")} for m in ps],
    }
    out = {"model": model_info(model), "settings": {"options": OPTIONS, "think": False, "prompt_round": PROMPT_ROUND},
           "agent_system_prompt": AGENT_SYSTEM, "extract_system_prompt": EXTRACT_SYSTEM,
           "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
           "summary": summary, "tool_cases": tool_rows, "refusals": refusal_rows, "extraction": extract_rows}
    suffix = "" if PROMPT_ROUND == "v1" else "__v2"
    path = RESULTS / (model.replace(":", "_").replace("/", "_") + suffix + ".json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    httpx.post(f"{OLLAMA}/api/generate", json={"model": model, "keep_alive": 0}, timeout=120)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"saved {path}")


def print_summary():
    for path in sorted(RESULTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        print(path.name, json.dumps(data["summary"], ensure_ascii=False))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--v2"]
    if args == ["--summary"]:
        print_summary()
    else:
        run(args[0])
