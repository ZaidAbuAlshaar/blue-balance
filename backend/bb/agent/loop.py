"""Blue Balance agent loop: prefilter -> Ollama tool calls -> number check -> rewrite / template / no-evidence.

Hard rules live here in code, not in the prompt:
- the refusal prefilter runs before the model sees the question;
- there is no approve tool; approval requests get a fixed line;
- tools run through `services`, which checks the role from the session `user` (never from chat text);
- at most 4 tool calls and a 25 s wall-clock budget per question;
- tool results are wrapped as JSON data in role "tool" and scrubbed of chat-template/bidi tokens;
- every number in the final answer must match this turn's tool results (numcheck), else rewrite x2, else template.
"""
import json
import re
import time

import httpx

from bb import config
from bb.agent import numcheck, refusal
from bb.agent.prompts import AGENT_SYSTEM_V2, TOOLS, TOOL_NAMES, WRITE_TOOLS

MAX_TOOL_CALLS = 4
BUDGET_S = 25.0
MAX_REWRITES = 2
NO_EVIDENCE = "ما عندي دليل على هاد بالبيانات المتوفرة.\n\nI don't have evidence for that in the available data."
TEMPLATE_HEADER = "نص من القالب · Template answer"
_CTRL = re.compile("[\u0000-\u0008\u000b\u000c\u000e-\u001f​-‏‪-‮⁦-⁩﻿]")
_TEMPLATE_TOKENS = re.compile(r"<\|[^|>]{0,40}\|>|</?(?:system|assistant|user|tool)>", re.IGNORECASE)
_DEFAULT_LIMITS = {"get_priority_queue": 5, "propose_next_measurement": 3}


def scrub(value):
    """Strip control/bidi/zero-width chars and chat-template tokens from every string in a tool result."""
    if isinstance(value, str):
        return _TEMPLATE_TOKENS.sub("", _CTRL.sub("", value))
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def _spec(name):
    return next((t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name), None)


def validate_args(name, args):
    spec = _spec(name)
    if spec is None:
        return "unknown_tool"
    if not isinstance(args, dict):
        return "invalid_args"
    for key in spec.get("required", []):
        if args.get(key) in (None, ""):
            return "invalid_args"
    for key, value in args.items():
        prop = spec["properties"].get(key)
        if prop is None:
            continue
        if "enum" in prop and value not in prop["enum"]:
            return "invalid_args"
        if "pattern" in prop and not re.match(prop["pattern"], str(value)):
            return "invalid_args"
        if prop.get("type") == "integer":
            try:
                ivalue = int(value)
            except (TypeError, ValueError):
                return "invalid_args"
            if not prop.get("minimum", ivalue) <= ivalue <= prop.get("maximum", ivalue):
                return "invalid_args"
    return None


def dispatch(name, args, user, services, flags):
    """Run one tool through `services`. Role checks happen inside services; errors come back as data."""
    if name not in TOOL_NAMES:
        return {"error": "unknown_tool"}
    args = dict(args or {})
    if name in _DEFAULT_LIMITS:
        args.setdefault("limit", _DEFAULT_LIMITS[name])
        if str(args["limit"]).isdigit():  # clamp to the schema range (model asked "top 5" of a max-3 tool)
            prop = _spec(name)["properties"]["limit"]
            args["limit"] = max(prop["minimum"], min(prop["maximum"], int(args["limit"])))
    error = validate_args(name, args)
    if error:
        return {"error": error}
    allowed = {k for k in _spec(name)["properties"]}
    kwargs = {k: v for k, v in args.items() if k in allowed}
    if name == "ingest_field_result":
        note = kwargs.get("note")
        if note:
            note = scrub(str(note))[:300]
            if refusal.injection_flags(note):
                flags.append("possible_injection_in_note")
            kwargs["note"] = note
        else:
            kwargs["note"] = None
    try:
        result = getattr(services, name)(**kwargs, user=user)
    except Exception as exc:  # a service bug must not crash the agent
        return {"error": "service_error", "detail": type(exc).__name__}
    return scrub(result) if isinstance(result, dict) else {"error": "service_error"}


def _chat(client, messages, tools=None):
    body = {"model": config.AGENT_MODEL, "messages": messages, "stream": False, "think": False,
            "options": config.LLM_OPTIONS, "keep_alive": -1}
    if tools:
        body["tools"] = tools
    start = time.perf_counter()
    resp = client.post(f"{config.OLLAMA_URL}/api/chat", json=body)
    resp.raise_for_status()
    data = resp.json()
    timing = {"wall_s": round(time.perf_counter() - start, 3),
              "total_s": round(data.get("total_duration", 0) / 1e9, 3),
              "eval_count": data.get("eval_count")}
    return data.get("message") or {}, timing


def _args(call):
    args = (call.get("function") or {}).get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    return args if isinstance(args, dict) else {}


def evidence_ids(results):
    ids = []
    for result in results:
        for _, strings in [numcheck._walk(result)]:
            for s in strings:
                for i in numcheck.ID_RE.findall(s):
                    if i.startswith("EV-") and i not in ids:
                        ids.append(i)
    return ids


def _iv(d):
    return f"{d['mean']} ({d['lo']}–{d['hi']})" if isinstance(d, dict) and "mean" in d else str(d)


def template_answer(tool_calls):
    """Build an answer in code from tool-result facts only (every number is copied, none computed)."""
    lines = []
    for call in tool_calls:
        name, r = call["name"], call["result"]
        if not isinstance(r, dict):
            continue
        if r.get("error") == "not_permitted":
            lines.append(f"- {name}: هاد الإجراء مش ضمن صلاحيات دورك · not permitted for your role")
            continue
        if r.get("error") == "unknown_case_id":
            lines.append(f"- {call['args'].get('case_id', '?')}: رقم حالة مش موجود · unknown case ID")
            continue
        if r.get("error"):
            lines.append(f"- {name}: {r['error']}")
            continue
        label = r.get("label", "")
        if name == "get_priority_queue":
            for row in r.get("queue", []):
                lines.append(f"- #{row.get('rank')} {row.get('case_id')} · p {_iv(row.get('p'))} · m³/insp-h "
                             f"{_iv(row.get('m3_per_insp_hour'))} [{row.get('evidence_id')} · {label}]")
        elif name == "query_posterior":
            ev = ", ".join(r.get("evidence_ids", []))
            lines.append(f"- {r.get('case_id')}: p {_iv(r.get('p'))} · m³/day {_iv(r.get('volume_m3_day'))} [{ev} · {label}]")
        elif name == "explain_ranking":
            t = r.get("terms", {})
            lines.append(f"- {r.get('case_id')} rank {r.get('rank')}: volume_m3_day {t.get('volume_m3_day')} · "
                         f"probability {t.get('probability')} · time_h {t.get('time_h')} [{label}]")
            for c in r.get("layer_contributions", []):
                lines.append(f"  - {c.get('layer')}: {c.get('signal')} [{c.get('evidence_id')}]")
        elif name == "propose_next_measurement":
            for m in r.get("measurements", []):
                lines.append(f"- {m.get('measurement_id')} {m.get('kind')} → {m.get('target_id')} · "
                             f"{m.get('expected_info_gain_bits')} bits · {m.get('cost_h')} h [{m.get('evidence_id')} · {label}]")
        elif name == "create_work_order_draft":
            lines.append(f"- {r.get('wo_id')}: مسودة بانتظار موافقة مهندس ثاني · draft, status {r.get('status')} [{label}]")
        elif name == "ingest_field_result":
            lines.append(f"- {r.get('result_id')}: posterior {r.get('posterior_before')} → {r.get('posterior_after')} · "
                         f"rank {r.get('rank_before')} → {r.get('rank_after')} [{label}]")
    return (TEMPLATE_HEADER + "\n" + "\n".join(lines)) if lines else None


def _result(answer, mode, tool_calls, checks, timing, t0):
    timing["total_s"] = round(time.perf_counter() - t0, 3)
    return {"answer": answer, "mode": mode, "tool_calls": tool_calls,
            "evidence_ids": evidence_ids([c["result"] for c in tool_calls]), "checks": checks,
            "model": config.AGENT_MODEL, "timing": timing}


def run_agent(question: str, user: dict, services, history: list | None = None, *,
              client: httpx.Client | None = None, budget_s: float = BUDGET_S) -> dict:
    t0 = time.perf_counter()
    timing = {"llm_calls": []}
    checks = {"prefilter": None, "flags": refusal.injection_flags(question), "rewrites": 0, "numcheck": [],
              "tool_budget_hit": False, "time_budget_hit": False}
    tool_calls = []

    code = refusal.prefilter(question)
    if code:
        checks["prefilter"] = code
        return _result(refusal.refusal_text(code, question), "refusal", tool_calls, checks, timing, t0)
    if refusal.is_approval_request(question):
        checks["prefilter"] = "APPROVAL"
        return _result(refusal.refusal_text("APPROVAL", question), "refusal", tool_calls, checks, timing, t0)

    messages = [{"role": "system", "content": AGENT_SYSTEM_V2}]
    for turn in history or []:  # only plain user/assistant text survives from history
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and isinstance(turn.get("content"), str):
            messages.append({"role": turn["role"], "content": turn["content"][:2000]})
    messages.append({"role": "user", "content": question})

    own_client = client is None
    client = client or httpx.Client(timeout=budget_s + 5)
    answer = ""
    try:
        while True:
            remaining = budget_s - (time.perf_counter() - t0)
            if remaining <= 0:
                checks["time_budget_hit"] = True
                break
            use_tools = len(tool_calls) < MAX_TOOL_CALLS
            msg, t = _chat(client, messages, TOOLS if use_tools else None)
            timing["llm_calls"].append(t)
            calls = (msg.get("tool_calls") or []) if use_tools else []
            if not calls:
                answer = (msg.get("content") or "").strip()
                break
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                name = (call.get("function") or {}).get("name", "")
                args = _args(call)
                if len(tool_calls) >= MAX_TOOL_CALLS:
                    checks["tool_budget_hit"] = True
                    result = {"error": "tool_budget_exceeded"}
                else:
                    result = dispatch(name, args, user, services, checks["flags"])
                    tool_calls.append({"name": name, "args": args, "result": result})
                messages.append({"role": "tool", "tool_name": name,
                                 "content": json.dumps({"tool_result_data": result}, ensure_ascii=False)})

        results = [c["result"] for c in tool_calls]
        allowed = set(numcheck.ID_RE.findall(numcheck.normalize(question)))
        while answer:
            check = numcheck.check_numbers(answer, results, allowed_ids=allowed)
            checks["numcheck"].append({k: check[k] for k in ("ok", "unmatched", "ids_unknown", "banned")})
            if check["ok"]:
                if not tool_calls:  # no tool was called: nothing grounds the answer
                    checks["model_draft"] = answer
                    return _result(NO_EVIDENCE, "no_evidence", tool_calls, checks, timing, t0)
                return _result(answer, "answer", tool_calls, checks, timing, t0)
            if checks["rewrites"] >= MAX_REWRITES or time.perf_counter() - t0 > budget_s:
                break
            checks["rewrites"] += 1
            problems = []
            if check["unmatched"]:
                problems.append("these numbers are not in your tool results: " + ", ".join(check["unmatched"]))
            if check["ids_unknown"]:
                problems.append("these IDs are not in your tool results: " + ", ".join(check["ids_unknown"]))
            if check["banned"]:
                problems.append("these phrases are not allowed: " + ", ".join(check["banned"]))
            messages.append({"role": "assistant", "content": answer})
            messages.append({"role": "user", "content": "Automatic checker: " + "; ".join(problems) +
                             ". Rewrite your answer: copy numbers exactly from the tool results or drop them. Same language."})
            msg, t = _chat(client, messages, None)
            timing["llm_calls"].append(t)
            answer = (msg.get("content") or "").strip()
    except (httpx.HTTPError, ValueError) as exc:
        checks["llm_error"] = type(exc).__name__
    finally:
        if own_client:
            client.close()

    succeeded = [c for c in tool_calls if isinstance(c["result"], dict)]
    text = template_answer(succeeded)
    if text:
        return _result(text, "template", tool_calls, checks, timing, t0)
    return _result(NO_EVIDENCE, "no_evidence", tool_calls, checks, timing, t0)
