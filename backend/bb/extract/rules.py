"""Rule-based crew-report extractor (offline, no model). Same output cells as the LLM path.

Built from the A7 U1.3 lexicon plus regex for IDs, sizes, flows and times. It is the baseline the LLM must beat.
"""
import re

from bb.extract import lexicon
from bb.extract.schema import FIELDS
from bb.extract.verify import empty

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_I = re.IGNORECASE
_LETTERS = {"تي": "T", "اف": "F", "إف": "F", "ال": "L", "إل": "L", "دبليو": "W", "اس": "S", "إس": "S", "دي": "D"}

SITE = re.compile(r"KRK[\s_-]*([A-Z])[\s_-]*(\d{3})(?!\d)", _I)
SITE_SPOKEN = re.compile(r"كي\s*(?:ا|أ|آ)ر\s*كي\s*(تي|اف|إف|ال|إل|دبليو|اس|إس|دي)\s*(\d{3})")
PLACES = ["القطرانة", "قطرانة", "المزار", "مؤتة", "الربة", "القصر", "فقوع", "الغور الصافي", "غور الصافي", "غور المزرعة",
          "الثنية", "السماكية", "العدنانية", "المرج", "عي", "أدر", "الطريق الصحراوي", "القلعة", "حي المطار",
          "الحي الشرقي", "الحي الغربي", "Qatraneh", "Al-Rabba", "Rabba", "Karak", "Mutah", "الكرك"]
PLACE_PREFIX = r"(?:(?:جنب|قرب|عند|مدخل|بلدة|بمنطقة|منطقة|شرق|غرب|شمال|جنوب|قبل|بعد|near|west of|east of|north of|south of)\s+(?:\S+\s+){0,2}?)?"
LOCATION = re.compile(PLACE_PREFIX + r"(?<!\w)(?:ب|في\s+)?(?:" + "|".join(re.escape(p) for p in sorted(PLACES, key=len, reverse=True)) + r")(?!\w)", _I)
ASSET = re.compile(
    r"(?:ال)?خط\s+(?:الرئيسي|الفرعي|الديسي|فرعي|رئيسي)(?:\s+\d+(?:\.\d+)?\s*(?:إنش|انش|\"))?"
    r"|(?:ال)?خط\s+\d+(?:\.\d+)?\s*(?:إنش|انش|\")|خط\s+(?:ال)?\w+"
    r"|(?:ال)?محبس(?:\s+رقم\s+\d+|\s+ال\w+(?:\s+ال\w+)?)?|(?:ال)?عداد(?:\s+ال\w+)?|بلف\s+\w+|(?:ال)?خزان(?:\s+\w+)?"
    r"|main\s+line|the\s+\d+\"?\s*main|\bmain\b|valve\s*\S*|hydrant", _I)
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(إنش|انش|inch(?:es)?|\")|(?:(\d+(?:\.\d+)?)\s*(?:م³|م3|m3|كوب|لتر|m³)"
                  r"\s*(?:/\s*(?:ساعة|س|h|hr|day)|بال(?:ساعة|ساعه|دقيقة|يوم)|per\s+hour)?)", _I)
SIZE_WORDS = re.compile(r"(?:(?:ال)?قطر(?:ها)?\s+(?:\S+\s+)?)?(?:(انش|إنش)\s+ونص|نص\s+(?:انش|إنش)|(ماسور(?:ة|ه)\s+(?:انش|إنش)))")
DATETIME = re.compile(
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2})?|\d{1,2}/\d{1,2}/\d{4}"
    r"|الساع(?:ة|ه)\s+(?:\d{1,2}(?::\d{2})?|واحدة|ثنتين|ثلاث|اربع|أربع|خمس|ست|ستة|سبع|ثمان|تسع|عشر|حداش|اطناش)(?:\s+(?:و?نص|الصبح|الظهر|العصر|المسا|بالليل|صباحاً|مساءً))*"
    r"|\d{1,2}:\d{2}(?:\s*(?:الصبح|صباحاً|مساءً|am|pm))?|\b\d{1,2}\s*(?:am|pm)\b"
    r"|(?:ا)?مبارح(?:\s+(?:الصبح|الظهر|العصر|المسا|بالليل))?|يوم\s+(?:السبت|الأحد|الاحد|الاثنين|الثلاثاء|الأربعاء|الاربعاء|الخميس|الجمعة)(?:\s+(?:الصبح|الظهر|العصر|المسا))?",
    _I)
ACTION = re.compile(r"(?:(?<!\w)و?لازم|بدها|بدنا|منقترح|نقترح|يوصى|بنصح|منرجع|recommend|suggest|need(?:s)?)\b[^.\n،؟!]*", _I)
_MAIN_BEFORE = re.compile(r"(?:خط|الخط|line|main|الرئيسي|الفرعي|فرعي|رئيسي)\s*(?:\S+\s*)?$", _I)


def _cell(value, text, start, end):
    return {"value": value, "span": text[start:end], "start": start, "end": end, "status": "filled", "match": "rules"}


def extract_rules(text: str) -> dict:
    raw = text or ""
    t = raw.translate(_DIGITS)  # same length as raw
    out = {f: empty() for f in FIELDS}

    m = SITE.search(t)
    if m:
        out["site_id"] = _cell(f"KRK-{m.group(1).upper()}-{m.group(2)}", raw, m.start(), m.end())
    else:
        m = SITE_SPOKEN.search(t)
        if m:
            out["site_id"] = _cell(f"KRK-{_LETTERS[m.group(1)]}-{m.group(2)}", raw, m.start(), m.end())

    m = LOCATION.search(t)
    if m:
        out["location"] = _cell(raw[m.start():m.end()].strip(), raw, m.start(), m.end())
    m = ASSET.search(t)
    if m:
        out["nearest_asset"] = _cell(raw[m.start():m.end()], raw, m.start(), m.end())

    for field in ("observation_type", "water_use", "evidence_attached", "severity"):
        cues = lexicon.find_cues(t, field)
        if field == "observation_type":
            nothing = [c for c in cues if c[0] == "nothing_found"]
            cues = nothing or cues
        if field == "evidence_attached":
            pick = [c for c in cues if c[0] == "none"] or [c for c in cues if c[0] == "video"] or cues
            cues = pick
        if cues:
            value, s, e = cues[0]
            out[field] = _cell(value, raw, s, e)

    for m in SIZE.finditer(t):
        if _MAIN_BEFORE.search(t[max(0, m.start() - 25): m.start()]):
            continue  # the size of the main line, not of the tap/leak
        number = m.group(1) or m.group(3)
        unit = m.group(2) or "m3/h"
        out["flow_or_size"] = _cell(f"{number} {unit}".strip(), raw, m.start(), m.end())
        break
    if out["flow_or_size"]["status"] != "filled":
        m = SIZE_WORDS.search(t)
        if m:
            value = "1.5 inch" if m.group(1) else ("1 inch" if m.group(2) else "0.5 inch")
            out["flow_or_size"] = _cell(value, raw, m.start(), m.end())

    m = DATETIME.search(t)
    if m:
        out["datetime"] = _cell(raw[m.start():m.end()], raw, m.start(), m.end())
    m = ACTION.search(t)
    if m:
        out["notes_action"] = _cell(raw[m.start():m.end()].strip(), raw, m.start(), m.end())
    return out
