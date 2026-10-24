"""Cue lexicon for the enum fields (A7 U1.3), shared by rules.py (baseline) and guard.py (conflict check).

Patterns run on the digit-normalised report (same length as the original, so offsets hold).
A cue preceded closely by a negator («ما صورنا», «لا بير», "no photos") does not count for its value.
"""
import re

_I = re.IGNORECASE

CUES = {
    "observation_type": {
        "nothing_found": [r"ما\s*لقينا\s*(?:ا|إ)?شي", r"ما\s*لقوا\s*(?:ا|إ)?شي", r"ما\s*في\s*(?:ا|إ)شي", r"لا\s*يوجد\s*(?:ا|أ)ي",
                          r"لم\s*يتم\s*العثور", r"ما\s*لقينا\s*(?:اي|أي)", r"nothing\s+found", r"no\s+anomal", r"انشالت",
                          r"لا\s*توجد\s*(?:اي|أي)"],
        "illegal_tap": [r"توصيل(?:ة|ه|ات)", r"وصل(?:ة|ه)(?!\s*عداد)", r"ماسور(?:ة|ه)\s*(?:\S+\s*){0,3}(?:موصول|مربوط|طالع|سحب)",
                        r"موصول(?:ة|ه)", r"مربوط", r"ربطة", r"خرطوم", r"bypass", r"\btap\b", r"connection", r"hydrant",
                        r"(?:ب|ي|عم\s*)?يعبي|بعبي|تعبئة"],
        "leak": [r"تسريب", r"تسرب", r"بتنقط", r"بتسرب", r"مي\s+طالعة", r"سايحة", r"فيضان", r"كسر", r"مكسور",
                 r"\bleak"],
        "illegal_well": [r"(?<!\w)(?:ال|ب|و|ف)?بير(?!\w)", r"بئر", r"\bwell\b", r"ارتوازي"],
        "irrigated_field": [r"مزروع(?:ة|ه)?", r"زراعة", r"تنقيط", r"irrigated", r"green\s+patch", r"drip"],
    },
    "water_use": {
        "farm": [r"مزرع(?:ة|ه)", r"مزارع", r"زيتون", r"خضرة", r"بندور", r"شعير", r"بطيخ", r"نخيل", r"دواجن",
                 r"زراعي", r"\bfarm", r"olive", r"crop"],
        "tanker_filling": [r"تنك", r"صهريج", r"tanker"],
        "homes": [r"بيوت(?!\s*شعر)", r"بيتين", r"منازل", r"\bhomes?\b", r"houses?"],
        "livestock": [r"غنم", r"مواشي", r"حلال", r"ماعز", r"بقر", r"livestock", r"sheep"],
        "none": [r"لا\s*يوجد\s*استخدام", r"ما\s*في\s*استخدام", r"no\s+(?:visible\s+)?use"],
    },
    "evidence_attached": {
        "video": [r"فيديو", r"video"],
        "photo": [r"صورنا(?!\s*فيديو)", r"صور(?:ة|ه|تين)", r"\bصور\b", r"التصوير", r"photos?", r"pictures?", r"صوّرنا"],
        "none": [r"ما\s*صورنا", r"ما\s*معنا\s*صور", r"بدون\s*صور", r"ما\s*لحقنا\s*نصور", r"ماخدنا\s*صور",
                 r"ما\s*في\s*صور", r"no\s+photos?", r"ماصورنا"],
    },
    "severity": {
        "low": [r"منخفض(?:ة|ه)?", r"بسيط(?:ة|ه)?", r"خفيف(?:ة|ه)?", r"ما\s*في\s*خط(?:ر|ورة|وره)", r"لا\s*توجد\s*خطورة",
                r"\blow\b"],
        "medium": [r"متوسط(?:ة|ه)?", r"\bmedium\b", r"moderate"],
        "high": [r"عالي(?:ة|ه)", r"خطير(?:ة|ه)?", r"\bhigh\b", r"severe", r"كبير"],
    },
}

# Negators: a cue preceded by one of these within 2 words is ignored (the "none" cues carry their own negator).
_NEG = re.compile(r"(?:^|[\s،,.])(?:ما|وما|مش|ومش|مو|لا|ولا|بدون|غير|لم|ولم|no|not|without)\s*(?:\S+\s+){0,1}$", _I)

COMPILED = {f: {v: [re.compile(p, _I) for p in pats] for v, pats in vals.items()} for f, vals in CUES.items()}


def find_cues(text: str, field: str):
    """-> list of (value, start, end) for non-negated cues of `field` in `text` (already digit-normalised)."""
    hits = []
    for value, patterns in COMPILED[field].items():
        for pattern in patterns:
            for m in pattern.finditer(text):
                if value != "none" and field != "observation_type" and _NEG.search(text[max(0, m.start() - 20): m.start()]):
                    continue
                if field == "observation_type" and value != "nothing_found" and _NEG.search(text[max(0, m.start() - 20): m.start()]):
                    continue
                hits.append((value, m.start(), m.end()))
    # A "none" evidence cue covers the photo cue inside it («ما صورنا» contains «صورنا»).
    nones = [(s, e) for v, s, e in hits if v == "none"]
    hits = [h for h in hits if h[0] == "none" or not any(s <= h[1] < e for s, e in nones)]
    return sorted(hits, key=lambda h: h[1])
