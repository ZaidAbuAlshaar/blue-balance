"""Deterministic span verification: a span survives only if it is an exact substring of the report.

Exact match first; otherwise a normalised match (digits, diacritics, tatweel, bidi, whitespace, case)
mapped back to original offsets. A failed span blanks the field (status "empty_no_evidence").
"""
import re

from bb.extract.schema import ENUMS, FIELDS

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_DROP = set("ًٌٍَُِّْـ​‌‍‎‏؜"
            "‪‫‬‭‮⁦⁧⁨⁩﻿")
_SITE = re.compile(r"^KRK-[A-Z]-\d{3}$")


def norm_with_map(text: str):
    """Normalise char by char; return (normalised, index_map) where index_map[i] = original index."""
    out, idx = [], []
    prev_space = True
    for i, ch in enumerate(text or ""):
        if ch in _DROP:
            continue
        ch = ch.translate(_DIGITS).lower()
        if ch.isspace():
            if prev_space:
                continue
            ch, prev_space = " ", True
        else:
            prev_space = False
        out.append(ch)
        idx.append(i)
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def norm(text: str) -> str:
    return norm_with_map(text)[0]


def locate(report: str, span: str):
    """-> (start, end, method) with method "exact" | "normalized", or None."""
    if not span or not isinstance(span, str):
        return None
    pos = report.find(span)
    if pos >= 0:
        return pos, pos + len(span), "exact"
    nrep, imap = norm_with_map(report)
    for candidate in (span, span.strip(" \"'«»“”،,.:;")):
        nspan = norm(candidate)
        if not nspan:
            continue
        pos = nrep.find(nspan)
        if pos >= 0:
            start = imap[pos]
            end = imap[pos + len(nspan) - 1] + 1
            return start, end, "normalized"
    return None


def empty(reason=None):
    cell = {"value": None, "span": None, "start": None, "end": None, "status": "empty_no_evidence"}
    if reason:
        cell["reason"] = reason
    return cell


def clean_value(field, value):
    """Type/enum check on the model's value. Returns (value, reason_if_rejected)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None
    if field in ENUMS:
        return (value, None) if value in ENUMS[field] else (None, "value_not_in_enum")
    value = str(value).strip()
    if field == "site_id":
        value = re.sub(r"[\s_]+", "-", value.translate(_DIGITS).upper())
        value = re.sub(r"-+", "-", value)
        m = re.match(r"^KRK-?([A-Z])-?(\d{3})$", value)
        if not m:
            return None, "site_id_pattern"
        value = f"KRK-{m.group(1)}-{m.group(2)}"
    return value, None


def verify_fields(report: str, fields: dict, flags: list | None = None) -> dict:
    """Turn raw {field: {value, span}} into verified cells with offsets."""
    flags = flags if flags is not None else []
    out = {}
    for field in FIELDS:
        pred = fields.get(field) if isinstance(fields, dict) else None
        pred = pred if isinstance(pred, dict) else {}
        value, reason = clean_value(field, pred.get("value"))
        if reason:
            flags.append(f"{reason}:{field}")
        if value is None:
            out[field] = empty(reason)
            continue
        hit = locate(report, pred.get("span"))
        if not hit:
            flags.append(f"span_not_found:{field}")
            out[field] = empty("span_not_found")
            continue
        start, end, method = hit
        span = report[start:end]
        if field == "flow_or_size":
            span_digits = re.findall(r"\d+(?:\.\d+)?", norm(span).replace("٫", "."))
            value_digits = re.findall(r"\d+(?:\.\d+)?", norm(value).replace("٫", "."))
            if span_digits and value_digits and not set(value_digits) & set(span_digits):
                flags.append("number_not_in_span:flow_or_size")
                out[field] = empty("number_not_in_span")
                continue
        out[field] = {"value": value, "span": span, "start": start, "end": end, "status": "filled", "match": method}
    return out
