"""Injection guard for crew reports (needed because Gemma obeyed the injected line in bake-off case C10).

1. Flag instruction-like text («تجاهل», «اكتب إنه», «وافق», "ignore previous", "approve").
2. Any field (except notes_action) whose span sits inside an instruction-like sentence -> needs_confirmation.
3. Enum fields whose report has cue words for 2+ different values -> needs_confirmation, value blanked,
   all candidate spans kept. The crew always confirms in the UI before submit.
"""
import re

from bb.extract import lexicon
from bb.extract.schema import ENUMS
from bb.extract.verify import norm_with_map

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
INSTRUCTION = re.compile(
    r"تجاهل|تجاهلي|انس(?:ى|ي)\s+(?:كل\s+)?(?:التعليمات|القواعد)|اكتب(?:وا)?\s+(?:إنه|انه|إن|ان|أنه)"
    r"|(?<!\w)و?وافق(?:وا)?\s+على|(?<!\w)و?اعتمد(?:وا)?\s+(?:الأمر|الامر|أمر|امر)|غي(?:ّ)?ر(?:وا)?\s+(?:الخطورة|الخطوره|التصنيف)"
    r"|\bignore\s+(?:all\s+|the\s+|your\s+|previous\s+|prior\s+|above\s+)*(?:instructions|rules|prompt)"
    r"|\bdisregard\b|\bapprove\b|\bset\s+(?:the\s+)?(?:observation_type|severity|field)|\bsystem\s*:|<\|",
    re.IGNORECASE)
_SENT_END = re.compile(r"[.!؟?\n]")


def instruction_ranges(text: str):
    """(start, end) of each sentence that contains instruction-like text."""
    ranges = []
    for m in INSTRUCTION.finditer(text or ""):
        start = max((e.end() for e in _SENT_END.finditer(text, 0, m.start())), default=0)
        nxt = _SENT_END.search(text, m.end())
        end = nxt.end() if nxt else len(text)
        if not ranges or start > ranges[-1][1]:
            ranges.append((start, end))
        else:
            ranges[-1] = (ranges[-1][0], max(end, ranges[-1][1]))
    return ranges


def instruction_flags(text: str) -> list[str]:
    return ["possible_injection"] if INSTRUCTION.search(text or "") else []


def _needs_confirmation(cell, candidates):
    return {"value": None, "span": None, "start": None, "end": None, "status": "needs_confirmation",
            "suggested": cell.get("value"), "candidates": candidates}


def apply(text: str, fields: dict, flags: list) -> dict:
    """Mutates and returns `fields`; appends flags."""
    ranges = instruction_ranges(text)
    if ranges and "possible_injection" not in flags:
        flags.append("possible_injection")
    for field, cell in fields.items():
        if field == "notes_action" or cell.get("status") != "filled":
            continue
        if any(cell["start"] < e and cell["end"] > s for s, e in ranges):
            fields[field] = _needs_confirmation(cell, [{k: cell[k] for k in ("value", "span", "start", "end")}])
            flags.append(f"span_in_instruction:{field}")

    ntext = (text or "").translate(_DIGITS)  # same length, offsets hold
    for field in ENUMS:
        cues = lexicon.find_cues(ntext, field)
        values = []
        for value, _, _ in cues:
            if value not in values:
                values.append(value)
        if len(values) < 2:
            continue
        candidates = []
        for value in values:
            value_cues = [c for c in cues if c[0] == value]
            _, s, e = value_cues[-1]
            candidates.append({"value": value, "span": text[s:e], "start": s, "end": e})
        cell = fields[field]
        if cell.get("status") == "needs_confirmation":
            known = {c["value"] for c in cell["candidates"]}
            cell["candidates"].extend(c for c in candidates if c["value"] not in known)
        else:
            fields[field] = _needs_confirmation(cell, candidates)
        flags.append(f"conflicting_cues:{field}")
    return fields
