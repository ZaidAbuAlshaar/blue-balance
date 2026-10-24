"""Keyword pre-filter for the two refusal rules (A7 §0.3) plus the approval line.

R1 = legal conclusion / accusation, R2 = personal data / owner identity.
The refusal texts are fixed templates; the model never writes them.
"""
import re

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_STRIP = re.compile("[ً-ْـ​-‏؜‪-‮⁦-⁩]")
CASE_ID = re.compile(r"\bKRK-[A-Z]-\d{3}\b")

# R1: accusation or legal conclusion. Arabic matched as substrings (clitics attach), English on word boundaries.
R1_AR = ["حرامي", "حراميه", "حرامية", "سارق", "سرقة", "سرقه", "بيسرق", "يسرق", "سرق المي", "سرقوا", "مذنب",
         "مخالف", "مخالفة قانونية", "مخالفه قانونيه", "غرامة", "غرامه", "مخالفة للقانون", "غير قانوني", "يعاقب",
         "عقوبة", "عقوبه", "مجرم", "يحاسب", "احكم لي", "احكملي", "يحبس", "حبس"]
R1_EN = [r"thie(?:f|ves)", r"steal(?:s|ing)?", r"stole(?:n)?", r"theft", r"guilty", r"illegal", r"unlawful",
         r"criminal", r"fine(?:d)?\b(?!\s+(?:grained|tune))", r"punish(?:ed|ment)?", r"prosecut\w*", r"break(?:s|ing)? the law",
         r"broke the law", r"violat(?:or|ion|ing)"]
# R2: personal data / identity.
R2_AR = ["مين صاحب", "مين اللي ساكن", "مين ساكن", "مين بيملك", "مين مالك", "مالك الأرض", "مالك الارض", "اسمه",
         "اسمها", "اسم صاحب", "اسم المالك", "اسم المزارع", "رقم وطني", "الرقم الوطني", "رقمه الوطني", "رقم تلفون",
         "رقم تلفونه", "تلفونه", "رقم هاتف", "رقم الهاتف", "رقم جوال", "رقم موبايل", "موبايله", "جواله", "عنوان بيته",
         "وين ساكن", "هويته", "هوية صاحب"]
R2_EN = [r"who\s+owns", r"owner(?:'s|s)?", r"owned\s+by", r"(?:his|her|their|whose|full|farmer'?s?)\s+name",
         r"name\s+of\s+the", r"phone(?:\s+number)?", r"mobile\s+number", r"national\s+id", r"id\s+number",
         r"home\s+address", r"where\s+(?:does\s+)?(?:he|she|they)\s+live"]
# Negators that cancel an R1 cue right before it (e.g. «ما لقوا إشي مخالف», "not illegal").
_NEG = re.compile(r"(?:^|\s)(?:ما|وما|مش|ومش|مو|ليس|ليست|لا|لم|ولا|ولم|بدون|غير|not|no|never|without|isn't|wasn't)\s+(?:\S+\s+){0,2}$")

APPROVAL = re.compile(
    r"(?:(?<!\w)(?:و?وافق(?:وا|ي)?|و?اعتمد(?:وا|ي)?|و?اعتمِد|و?صادق|و?مرر|مرّر)\b(?!\s*(?:عليه\s+)?المهندس))"
    r"|\b(?:approve[sd]?|approving|sign\s+off|authori[sz]e)\b", re.IGNORECASE)
INJECTION = re.compile(
    r"تجاهل|انسى\s+(?:كل\s+)?(?:التعليمات|القواعد)|اكتب(?:لي)?\s+(?:إنه|انه|إن|ان)\b|غيّر\s+(?:القواعد|التعليمات)"
    r"|\bignore\s+(?:all\s+|your\s+|the\s+|previous\s+|prior\s+)*(?:instructions|rules|prompt)|\bdisregard\b"
    r"|\byou\s+are\s+now\b|\bsystem\s*:|<\|", re.IGNORECASE)

TEMPLATES = {
    "R1": {
        "ar": "ما بقدر أحكم إذا حدا سارق أو مخالف، هاد قرار قانوني للجهات المختصة. اللي بقدر أعطيك إياه: ترتيب {case} بقائمة التفتيش والأدلة اللي وراه، والقرار للمفتش بعد الزيارة.",
        "en": "I can't decide whether anyone broke the law; that is for the authorities. I can show where {case_en} sits in the inspection queue and the evidence behind it. The inspector decides after the visit.",
    },
    "R2": {
        "ar": "النظام ما فيه أسماء أصحاب أراضي أو آبار أو أرقام تلفونات أو أرقام وطنية، وهاد مقصود. القطع والمواقع معرّفة بأرقام داخلية بس.",
        "en": "The system holds no owner names, phone numbers, national IDs or other personal data, by design. Sites are referenced by internal IDs only.",
    },
    "APPROVAL": {
        "ar": "ما بقدر أوافق على أوامر العمل ولا أعتمدها. الموافقة بتصير من شاشة أوامر العمل (Work Orders) من مهندس ثاني غير اللي طلب الأمر. بقدر أجهّزلك مسودة بس.",
        "en": "I can't approve work orders. Approval happens on the Work Orders screen, by a different engineer from the one who requested it. I can only prepare drafts.",
    },
}


def normalize(text: str) -> str:
    text = _STRIP.sub("", (text or "").translate(_AR_DIGITS))
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return re.sub(r"\s+", " ", text).strip()


def _norm_terms(terms):
    return [normalize(t) for t in terms]


_R1_AR, _R2_AR = _norm_terms(R1_AR), _norm_terms(R2_AR)
_R1_EN = re.compile(r"\b(?:" + "|".join(R1_EN) + r")", re.IGNORECASE)
_R2_EN = re.compile(r"\b(?:" + "|".join(R2_EN) + r")\b", re.IGNORECASE)


def _ar_hit(text, terms, negatable):
    for term in terms:
        for m in re.finditer(re.escape(term), text):
            if negatable and _NEG.search(text[: m.start()]):
                continue
            return True
    return False


def _en_hit(text, pattern, negatable):
    for m in pattern.finditer(text):
        if negatable and _NEG.search(text[: m.start()].lower()):
            continue
        return True
    return False


def prefilter(question: str) -> str | None:
    """Return "R2" (personal data), "R1" (accusation/legal) or None. R2 wins when both match."""
    text = normalize(question)
    if _ar_hit(text, _R2_AR, False) or _en_hit(text, _R2_EN, False):
        return "R2"
    if _ar_hit(text, _R1_AR, True) or _en_hit(text, _R1_EN, True):
        return "R1"
    return None


def is_approval_request(question: str) -> bool:
    """True when the user asks the agent to approve/sign off something. No approve tool exists."""
    return bool(APPROVAL.search(normalize(question)))


def injection_flags(text: str) -> list[str]:
    return ["possible_injection"] if INJECTION.search(normalize(text)) else []


def refusal_text(code: str, question: str = "") -> str:
    tpl = TEMPLATES[code]
    ids = CASE_ID.findall(normalize(question))
    case_ar = f"الحالة {ids[0]}" if ids else "الحالات"
    case_en = ids[0] if ids else "each case"
    ar = tpl["ar"].format(case=case_ar)
    en = tpl["en"].format(case_en=case_en)
    return f"{ar}\n\n{en}"
