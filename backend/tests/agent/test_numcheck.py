"""Number-checker unit tests: 50+ AR/EN strings. No GPU, no Ollama."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "eval" / "bakeoff"))
from cases import run_tool  # noqa: E402

from bb.agent.numcheck import check_numbers, find_banned, normalize  # noqa: E402

QUEUE = run_tool("get_priority_queue", {"region_id": "KRK", "limit": 3})
POST = run_tool("query_posterior", {"case_id": "KRK-T-007"})
EXPL = run_tool("explain_ranking", {"case_id": "KRK-T-007"})
MEAS = run_tool("propose_next_measurement", {"region_id": "KRK", "limit": 3})
INGEST = run_tool("ingest_field_result", {"case_id": "KRK-F-012", "outcome": "no_anomaly_found"})
WO = run_tool("create_work_order_draft", {"case_id": "KRK-T-007"})
ALL = [QUEUE, POST, EXPL, MEAS, INGEST, WO]

PASS = [
    "احتمالية KRK-T-007 هي 0.62 [EV-SIM-101]",
    "احتمالية KRK-T-007 هي ٠٫٦٢ (من ٠٫٤١ إلى ٠٫٧٩) [EV-SIM-101]",
    "The probability is 62% (41–79%) [EV-SIM-101].",
    "الاحتمال ٦٢٪ [EV-SIM-101]",
    "الاحتمالية حوالي 0.6 [EV-SIM-101]",
    "Expected loss 310 m³/day, range 140-560 [EV-SIM-101]",
    "الكمية ٣١٠ م³ باليوم (١٤٠–٥٦٠) [EV-SIM-101]",
    "KRK-T-007 is rank 1 with 21.0 m3 per inspection hour [EV-SIM-101]",
    "KRK-L-003 rank 2, p 0.48 [EV-SIM-102]",
    "1. KRK-T-007\n2. KRK-L-003\n3. KRK-F-012",
    "- KRK-T-007: 21 m³/h\n- KRK-L-003: 6.5 m³/h",
    "الوقت المتوقع للتفتيش 2.5 ساعة",
    "likelihood ratio 3.4 [EV-SIM-101]",
    "أحسن قياس: M-SIM-01 على KRK-T-007، 0.71 bits، ساعة وحدة [EV-SIM-201]",
    "Info gain 0.71 bits at a cost of 1.0 h [EV-SIM-201]",
    "Info gain 0.7 bits [EV-SIM-201]",
    "الاحتمال نزل من 0.35 إلى 0.08 والترتيب من 3 إلى 5",
    "Posterior moved from 35% to 8%.",
    "تم إنشاء المسودة WO-SIM-0001 وهي بانتظار الموافقة",
    "Draft WO-SIM-0001 created, pending approval by another engineer.",
    "ما عندي دليل على هاد بالبيانات المتوفرة.",
    "No numbers here at all.",
    "الاحتمال 0.62 والفترة 0.41–0.79 [EV-SIM-101 · Simulated]",
    "النتيجة FR-SIM-0001 سجلت",
    "‏٦٢‏٪ [EV-SIM-101]",
    "p = 0.62 (90% interval 0.41-0.79)",
]
FAIL = [
    ("احتمالية KRK-T-007 هي 0.65", "0.65"),
    ("الاحتمال ٧٠٪", "70%"),
    ("Expected loss 900 m³/day", "900"),
    ("الكمية ١٫٢ مليون م³ بالسنة", "1.2 مليون"),
    ("About 2 thousand m3 a day", "2 thousand"),
    ("total of the top three is 470 m³/day", "470"),
    ("KRK-T-099 is also suspicious", None),
    ("See evidence EV-SIM-999", None),
    ("الحالة KRK-X-123 أعلى", None),
    ("rank 17 of 23", "17"),
    ("visit on 2026-10-30", "2026-10-30"),
    ("الزيارة الساعة 10:30", "10:30"),
    ("p = 0.623", "0.623"),
    ("about 300 m³/day", "300"),
    ("الاحتمال 63٪", "63%"),
    ("loss is 12.5 m3/h", "12.5"),
]
BANNED_FAIL = [
    "صاحب KRK-T-007 حرامي",
    "هاي سرقة مؤكدة عند KRK-T-007",
    "The owner is a thief.",
    "He is guilty of taking water.",
    "Somebody stole water at KRK-T-007.",
    "المزارع سارق المي",
    "theft confirmed at KRK-T-007",
]
BANNED_OK = [
    "ما بقدر أحكم إذا حدا سارق أو مخالف، هاد قرار قانوني للجهات المختصة.",
    "I can't say anyone is a thief; that is for the authorities.",
    "This is not theft confirmed; it is a candidate.",
    "مش حرامي ولا مذنب، هاي حالة مرشحة للتفتيش بس",
    "Nobody is guilty here; it is an inspection candidate.",
]


@pytest.mark.parametrize("answer", PASS)
def test_grounded_answers_pass(answer):
    result = check_numbers(answer, ALL)
    assert result["ok"], result


@pytest.mark.parametrize("answer,bad", FAIL)
def test_ungrounded_answers_fail(answer, bad):
    result = check_numbers(answer, ALL)
    assert not result["ok"], result
    if bad:
        assert any(bad.split()[0] in u for u in result["unmatched"]), result


@pytest.mark.parametrize("answer", BANNED_FAIL)
def test_banned_phrases_fail(answer):
    result = check_numbers(answer, ALL)
    assert not result["ok"] and result["banned"], result


@pytest.mark.parametrize("answer", BANNED_OK)
def test_negated_banned_phrases_pass(answer):
    assert find_banned(answer) == [], answer


def test_unknown_ids_reported():
    result = check_numbers("KRK-T-099 and EV-SIM-999", ALL)
    assert result["ids_unknown"] == ["EV-SIM-999", "KRK-T-099"]


def test_question_ids_allowed():
    result = check_numbers("KRK-D-002 مش موجودة بالبيانات", [{"error": "unknown_case_id"}], allowed_ids={"KRK-D-002"})
    assert result["ok"], result


def test_numbers_need_this_turns_tools():
    assert not check_numbers("0.62", [])["ok"]
    assert not check_numbers("0.62", [MEAS])["ok"]


def test_normalize_digits_and_marks():
    assert normalize("٠١٢٣٤٥٦٧٨٩ ٫ ٬ ٪‎") == "0123456789 . , %"


def test_matched_numbers_carry_evidence_ids():
    result = check_numbers("p 0.62", [POST])
    assert result["matched"][0]["evidence_id"] == "EV-SIM-101"


def test_case_count():
    assert len(PASS) + len(FAIL) + len(BANNED_FAIL) + len(BANNED_OK) >= 40
