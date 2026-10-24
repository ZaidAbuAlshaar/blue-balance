"""Deterministic number checker (A7 §0.2). Runs on every final agent answer before it is shown.

A number in the answer passes only if it matches a number in THIS turn's tool results:
exactly, rounded to the precision written, or a 0-1 fraction written as a percentage.
Derived numbers (sums, differences, unit conversions) do not pass: a tool must compute them.
"""
import re
from typing import Iterable

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SEP = str.maketrans({"٫": ".", "٬": ",", "٪": "%", "−": "-", "–": "-", "—": "-"})
_BIDI = re.compile("[‎‏؜‪-‮⁦-⁩​-‍﻿]")
_SPACES = re.compile("[    ]")

ID_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?![A-Za-z0-9])")
DATE_RE = re.compile(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}/\d{1,2}/\d{1,2})\b|\b\d{1,2}:\d{2}\b")
UNIT_RE = re.compile(r"(?:(?<=[A-Za-z])|(?<=م))[³²]|\b(?:m3|m2|co2|h2o|km2)\b|م3(?![0-9])", re.IGNORECASE)
# Project convention, not a claim: every interval is a 90% interval (CONTRACTS.md shared conventions).
CONVENTION_RE = re.compile(r"90\s*%\s*(?:interval|CI|credible|confidence)|(?:فترة|فتره|مجال)\s*(?:ثقة\s*)?90\s*%|90\s*%\s*(?:فترة|مجال)", re.IGNORECASE)
LIST_MARKER = re.compile(r"(?m)^\s*(?:\d{1,2}[.)]|[-*•])\s+")
NUM_RE = re.compile(
    r"(?<![A-Za-z0-9.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(\s*(?:%|بالمية|بالمئة|في المية|في المئة|percent\b))?"
    r"(\s*(?:ألف|الف|آلاف|الاف|thousand\b|مليون|ملايين|million\b|مليار|billion\b))?", re.IGNORECASE)
_RANGE_PCT = re.compile(r"\s*(?:-|to|إلى|الى|لـ|ل|و)\s*\d+(?:\.\d+)?\s*(?:%|بالمية|بالمئة|percent)", re.IGNORECASE)
SCALE = {"ألف": 1e3, "الف": 1e3, "آلاف": 1e3, "الاف": 1e3, "thousand": 1e3, "مليون": 1e6, "ملايين": 1e6,
         "million": 1e6, "مليار": 1e9, "billion": 1e9}

BANNED_AR = ["سرقة مؤكدة", "سرقه مؤكده", "حرامي", "حرامية", "سارق", "مذنب"]
BANNED_EN = [r"theft\s+(?:is\s+)?confirmed", r"confirmed\s+theft", r"thie(?:f|ves)", r"guilty", r"stole(?:n)?"]
_BANNED_EN = re.compile(r"\b(?:" + "|".join(BANNED_EN) + r")\b", re.IGNORECASE)
_NEG_BEFORE = re.compile(
    r"(?:^|[\s،,.(])(?:ما|وما|مش|ومش|مو|ليس|ليست|لا|لم|لن|ولا|ولم|بدون|غير|مستحيل|not|no|never|cannot|can't|isn't|aren't|won't|without|nobody|neither|nor)"
    r"(?:\s+\S+){0,5}\s*$", re.IGNORECASE)


def normalize(text: str) -> str:
    text = (text or "").translate(_DIGITS).translate(_SEP)
    text = _BIDI.sub("", text)
    return _SPACES.sub(" ", text)


def _walk(obj, ev=None, out=None, strings=None):
    """Collect (number, evidence_id) pairs and all strings from a tool result."""
    out = [] if out is None else out
    strings = [] if strings is None else strings
    if isinstance(obj, dict):
        local = obj.get("evidence_id") or (obj.get("evidence_ids") or [None])[0] or ev
        for key, value in obj.items():
            _walk(value, local, out, strings)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            _walk(value, ev, out, strings)
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        out.append((float(obj), ev))
    elif isinstance(obj, str):
        strings.append(obj)
        masked = ID_RE.sub(" ", normalize(obj))
        for m in NUM_RE.finditer(masked):
            out.append((float(m.group(1).replace(",", "")), ev))
    return out, strings


def known_ids(tool_results: Iterable[dict]) -> set[str]:
    ids = set()
    for _, strings in (_walk(r) for r in tool_results):
        for s in strings:
            ids.update(ID_RE.findall(normalize(s)))
    return ids


def _decimals(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def _match(value: float, decimals: int, is_pct: bool, scale: float, pool):
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    for number, ev in pool:
        if scale != 1:
            if abs(number / scale - value) <= tol or abs(number - value * scale) < 1e-6:
                return ev or True
            continue
        if abs(number - value) <= tol:
            return ev or True
        if is_pct and 0 <= number <= 1 and abs(number * 100 - value) <= tol:
            return ev or True
    return None


def find_banned(answer: str) -> list[str]:
    text = normalize(answer)
    hits = []
    for term in BANNED_AR:
        for m in re.finditer(re.escape(term), text):
            if not _NEG_BEFORE.search(text[: m.start()]):
                hits.append(term)
    for m in _BANNED_EN.finditer(text):
        if not _NEG_BEFORE.search(text[: m.start()]):
            hits.append(m.group(0).lower())
    return sorted(set(hits))


def check_numbers(answer: str, tool_results: list[dict], allowed_ids: Iterable[str] = ()) -> dict:
    """-> {"ok", "unmatched", "ids_unknown", "banned", "matched", "numbers_checked"}.

    allowed_ids: IDs the user typed in the question (e.g. an unknown case they asked about)."""
    text = normalize(answer)
    pool = []
    strings = []
    for result in tool_results:
        nums, strs = _walk(result)
        pool.extend(nums)
        strings.extend(strs)
    ids_known = known_ids(tool_results) | set(allowed_ids)
    ids_unknown = sorted({i for i in ID_RE.findall(text) if any(c.isdigit() for c in i) and i not in ids_known})

    masked = ID_RE.sub(" ⟦ID⟧ ", text)
    masked = CONVENTION_RE.sub(" interval ", masked)
    masked = LIST_MARKER.sub(" ", masked)
    masked = UNIT_RE.sub(" unit ", masked)
    unmatched, matched = [], []
    tool_text = " ".join(normalize(s) for s in strings)
    for m in DATE_RE.finditer(masked):
        if m.group(0) not in tool_text:
            unmatched.append(m.group(0))
    masked = DATE_RE.sub(" ⟦DATE⟧ ", masked)
    count = 0
    for m in NUM_RE.finditer(masked):
        token, pct, scale_word = m.group(1), m.group(2), m.group(3)
        if not pct and _RANGE_PCT.match(masked, m.end()):
            pct = "%"  # "41-79%": the % applies to both ends of the range
        count += 1
        value = float(token.replace(",", ""))
        scale = SCALE.get(scale_word.strip().lower(), 1) if scale_word else 1
        ev = _match(value, _decimals(token), bool(pct), scale, pool)
        if ev is None:
            unmatched.append(m.group(0).strip())
        else:
            matched.append({"text": m.group(0).strip(), "evidence_id": ev if isinstance(ev, str) else None})
    banned = find_banned(answer)
    return {"ok": not unmatched and not ids_unknown and not banned, "unmatched": unmatched,
            "ids_unknown": ids_unknown, "banned": banned, "matched": matched, "numbers_checked": count}
