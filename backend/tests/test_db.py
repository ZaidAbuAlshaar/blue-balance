"""The honesty rules are enforced by the database, not only by the UI."""
import json
import sqlite3

import pytest

from bb import db


@pytest.fixture
def con(tmp_path):
    c = db.connect(tmp_path / "t.sqlite")
    db.init(c)
    c.execute("INSERT INTO cases VALUES ('KRK-T-001','transmission','{}','[]',1.0,1.0,'[\"EV-X-1\"]','[]')")
    return c


def test_label_must_be_one_of_four(con):
    with pytest.raises(sqlite3.IntegrityError):
        db.add_evidence(con, "EV-X-1", "guess", "k", "s", {})


def test_evidence_is_immutable(con):
    db.add_evidence(con, "EV-X-1", "Observed", "k", "s", {"a": 1})
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE evidence SET label = 'Field-verified' WHERE evidence_id = 'EV-X-1'")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM evidence WHERE evidence_id = 'EV-X-1'")


def test_posterior_needs_ordered_interval_and_evidence(con):
    good = {"mean": 0.5, "lo": 0.4, "hi": 0.6}
    db.add_posterior(con, "KRK-T-001", good, good, good, ["EV-X-1"], "ok", "system")
    with pytest.raises(sqlite3.IntegrityError):
        db.add_posterior(con, "KRK-T-001", {"mean": 0.7, "lo": 0.4, "hi": 0.6}, good, good, ["EV-X-1"], "bad", "system")
    with pytest.raises(sqlite3.IntegrityError):
        db.add_posterior(con, "KRK-T-001", good, good, good, [], "no evidence", "system")


def test_posteriors_are_append_only(con):
    iv = {"mean": 0.5, "lo": 0.4, "hi": 0.6}
    db.add_posterior(con, "KRK-T-001", iv, iv, iv, ["EV-X-1"], "ok", "system")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE posteriors SET p_mean = 0.9")


def test_work_order_cannot_be_self_approved(con):
    con.execute("""INSERT INTO work_orders (wo_id, case_id, task, priority, text_ar, text_en, crew_ar, status,
                   requested_by, requested_via, created_at)
                   VALUES ('WO-1','KRK-T-001','inspect_connection','high','a','b','c','pending_approval','eng_a','agent','t')""")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE work_orders SET status='approved', decided_by='eng_a', decided_at='t' WHERE wo_id='WO-1'")
    con.execute("UPDATE work_orders SET status='approved', decided_by='eng_b', decided_at='t' WHERE wo_id='WO-1'")


def test_map_edit_needs_evidence_and_other_approver(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("""INSERT INTO map_edits (edit_id, case_id, kind, geometry, evidence_ids, status, proposed_by, created_at)
                       VALUES ('ME-1','KRK-T-001','tap_location','{}','[]','draft','insp_1','t')""")
    con.execute("""INSERT INTO map_edits (edit_id, case_id, kind, geometry, evidence_ids, status, proposed_by, created_at)
                   VALUES ('ME-2','KRK-T-001','tap_location','{}',?,'draft','insp_1','t')""", (json.dumps(["EV-X-1"]),))
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE map_edits SET status='approved', decided_by='insp_1', decided_at='t' WHERE edit_id='ME-2'")


def test_field_result_cannot_claim_observed(con):
    iv = {"mean": 0.5, "lo": 0.4, "hi": 0.6}
    pid = db.add_posterior(con, "KRK-T-001", iv, iv, iv, ["EV-X-1"], "ok", "system")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("""INSERT INTO field_results VALUES ('FR-1','KRK-T-001','no_anomaly_found',NULL,'Observed','insp_1',?,?,'t')""",
                    (pid, pid))


def test_audit_chain_detects_nothing_wrong_and_blocks_edits(con):
    db.audit(con, "eng_a", "user", "login")
    db.audit(con, "eng_a", "agent", "agent_ask", None, {"mode": "answer"})
    assert db.verify_audit_chain(con) == {"ok": True}
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE audit_log SET actor = 'someone_else'")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM audit_log")
