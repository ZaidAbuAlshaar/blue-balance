"""Crew report -> 10 typed fields with verbatim source spans.

LLM path: Gemma (bb.config.EXTRACT_MODEL) with the JSON-schema `format` and the bake-off EXTRACT_SYSTEM prompt,
then span verification and the injection guard. If Ollama fails, the rule-based extractor runs (method "rules").
"""
import json
import time

import httpx

from bb import config
from bb.extract import guard, rules, verify
from bb.extract.schema import EXTRACT_SYSTEM, FIELDS, extraction_schema

TIMEOUT_S = 90


def call_llm(text: str, client: httpx.Client | None = None) -> tuple[dict, dict]:
    body = {"model": config.EXTRACT_MODEL, "stream": False, "think": False, "keep_alive": -1,
            "options": config.LLM_OPTIONS, "format": extraction_schema(),
            "messages": [{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": text}]}
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S)
    try:
        start = time.perf_counter()
        resp = client.post(f"{config.OLLAMA_URL}/api/chat", json=body)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if own:
            client.close()
    raw = json.loads((data.get("message") or {}).get("content") or "")
    if not isinstance(raw, dict):
        raise ValueError("extractor output is not an object")
    timing = {"wall_s": round(time.perf_counter() - start, 3), "total_s": round(data.get("total_duration", 0) / 1e9, 3)}
    return raw, timing


def extract_report(text: str, use_llm: bool = True, *, client: httpx.Client | None = None) -> dict:
    flags = guard.instruction_flags(text)
    method, model, timing, raw = "rules", None, {}, None
    fields = None
    if use_llm:
        try:
            raw, timing = call_llm(text, client)
            fields = verify.verify_fields(text, raw, flags)
            method, model = "llm", config.EXTRACT_MODEL
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            flags.append(f"llm_unavailable:{type(exc).__name__}")
    if fields is None:
        start = time.perf_counter()
        fields = rules.extract_rules(text)
        timing = {"wall_s": round(time.perf_counter() - start, 4)}
    fields = guard.apply(text, fields, flags)
    return {"fields": {f: fields[f] for f in FIELDS}, "method": method, "flags": flags, "model": model,
            "timing": timing, "raw": raw}
