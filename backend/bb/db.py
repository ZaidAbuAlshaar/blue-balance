"""SQLite store. The honesty rules are enforced here, not only in the UI:
evidence labels are a closed set, every quantity carries an interval, evidence and
posteriors are append-only, approvers differ from proposers, and the audit log is a
hash chain that cannot be edited."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from bb.config import DB_PATH

LABEL_CHECK = "label IN ('Observed','Simulated','Hypothesis','Field-verified')"

SCHEMA = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('inspector','engineer','admin')),
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    label TEXT NOT NULL CHECK ({LABEL_CHECK}),
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    method TEXT,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS evidence_no_update BEFORE UPDATE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_no_delete BEFORE DELETE ON evidence
BEGIN SELECT RAISE(ABORT, 'evidence is immutable'); END;

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY CHECK (case_id GLOB 'KRK-[TFL]-[0-9][0-9][0-9]'),
    layer TEXT NOT NULL CHECK (layer IN ('source','transmission','distribution')),
    geometry TEXT NOT NULL,
    linked_case_ids TEXT NOT NULL DEFAULT '[]',
    travel_h REAL NOT NULL CHECK (travel_h >= 0),
    inspect_h REAL NOT NULL CHECK (inspect_h > 0),
    evidence_ids TEXT NOT NULL CHECK (json_array_length(evidence_ids) >= 1),
    signals TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posteriors (
    posterior_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    version INTEGER NOT NULL,
    p_mean REAL NOT NULL, p_lo REAL NOT NULL, p_hi REAL NOT NULL,
    vol_mean REAL NOT NULL, vol_lo REAL NOT NULL, vol_hi REAL NOT NULL,
    m3h_mean REAL NOT NULL, m3h_lo REAL NOT NULL, m3h_hi REAL NOT NULL,
    label TEXT NOT NULL DEFAULT 'Hypothesis' CHECK ({LABEL_CHECK}),
    evidence_ids TEXT NOT NULL CHECK (json_array_length(evidence_ids) >= 1),
    reason TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (case_id, version),
    CHECK (0 <= p_lo AND p_lo <= p_mean AND p_mean <= p_hi AND p_hi <= 1),
    CHECK (vol_lo <= vol_mean AND vol_mean <= vol_hi),
    CHECK (m3h_lo <= m3h_mean AND m3h_mean <= m3h_hi)
);
CREATE TRIGGER IF NOT EXISTS posteriors_no_update BEFORE UPDATE ON posteriors
BEGIN SELECT RAISE(ABORT, 'posteriors are append-only'); END;
CREATE TRIGGER IF NOT EXISTS posteriors_no_delete BEFORE DELETE ON posteriors
BEGIN SELECT RAISE(ABORT, 'posteriors are append-only'); END;

CREATE TABLE IF NOT EXISTS field_results (
    result_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    outcome TEXT NOT NULL CHECK (outcome IN
        ('anomaly_found_leak','anomaly_found_connection','no_anomaly_found','inconclusive')),
    note TEXT,
    label TEXT NOT NULL CHECK (label IN ('Simulated','Field-verified')),
    submitted_by TEXT NOT NULL,
    posterior_before INTEGER NOT NULL REFERENCES posteriors(posterior_id),
    posterior_after INTEGER NOT NULL REFERENCES posteriors(posterior_id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crew_reports (
    report_id TEXT PRIMARY KEY,
    case_id TEXT REFERENCES cases(case_id),
    text TEXT NOT NULL,
    fields TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('llm','rules')),
    flags TEXT NOT NULL DEFAULT '[]',
    label TEXT NOT NULL CHECK (label IN ('Simulated','Field-verified')),
    confirmed_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_orders (
    wo_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    task TEXT NOT NULL CHECK (task IN ('inspect_connection','inspect_leak','inspect_field')),
    priority TEXT NOT NULL CHECK (priority IN ('high','medium','low')),
    text_ar TEXT NOT NULL, text_en TEXT NOT NULL, crew_ar TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending_approval','approved','rejected')),
    requested_by TEXT NOT NULL,
    requested_via TEXT NOT NULL CHECK (requested_via IN ('ui','agent')),
    decided_by TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL,
    CHECK (decided_by IS NULL OR decided_by <> requested_by),
    CHECK ((status = 'pending_approval') = (decided_by IS NULL))
);

CREATE TABLE IF NOT EXISTS map_edits (
    edit_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(case_id),
    kind TEXT NOT NULL CHECK (kind IN ('new_connection','tap_location','undocumented_segment')),
    geometry TEXT NOT NULL,
    evidence_ids TEXT NOT NULL CHECK (json_array_length(evidence_ids) >= 1),
    status TEXT NOT NULL CHECK (status IN ('draft','approved','rejected')),
    proposed_by TEXT NOT NULL,
    decided_by TEXT,
    reason TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    CHECK (decided_by IS NULL OR decided_by <> proposed_by),
    CHECK ((status = 'draft') = (decided_by IS NULL))
);

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    mode TEXT NOT NULL,
    tool_calls TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('user','agent','system')),
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path=None):
    con = sqlite3.connect(str(path or DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(con):
    con.executescript(SCHEMA)
    con.commit()


def audit(con, actor, actor_type, action, target=None, detail=None):
    """Append one hash-chained audit row."""
    row = con.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else "GENESIS"
    at = now()
    body = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(f"{prev}|{at}|{actor}|{actor_type}|{action}|{target}|{body}".encode()).hexdigest()
    con.execute(
        "INSERT INTO audit_log (at, actor, actor_type, action, target, detail, prev_hash, hash) VALUES (?,?,?,?,?,?,?,?)",
        (at, actor, actor_type, action, target, body, prev, digest))


def verify_audit_chain(con):
    prev = "GENESIS"
    for row in con.execute("SELECT * FROM audit_log ORDER BY seq"):
        expected = hashlib.sha256(
            f"{prev}|{row['at']}|{row['actor']}|{row['actor_type']}|{row['action']}|{row['target']}|{row['detail']}".encode()
        ).hexdigest()
        if row["prev_hash"] != prev or row["hash"] != expected:
            return {"ok": False, "broken_at": row["seq"]}
        prev = row["hash"]
    return {"ok": True}


def add_evidence(con, evidence_id, label, kind, source, payload, method=None):
    con.execute(
        "INSERT INTO evidence (evidence_id, label, kind, source, method, payload, created_at) VALUES (?,?,?,?,?,?,?)",
        (evidence_id, label, kind, source, method, json.dumps(payload, ensure_ascii=False), now()))


def latest_posterior(con, case_id):
    return con.execute(
        "SELECT * FROM posteriors WHERE case_id = ? ORDER BY version DESC LIMIT 1", (case_id,)).fetchone()


def add_posterior(con, case_id, p, vol, m3h, evidence_ids, reason, created_by):
    row = latest_posterior(con, case_id)
    version = (row["version"] + 1) if row else 1
    cur = con.execute(
        """INSERT INTO posteriors (case_id, version, p_mean, p_lo, p_hi, vol_mean, vol_lo, vol_hi,
           m3h_mean, m3h_lo, m3h_hi, evidence_ids, reason, created_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (case_id, version, p["mean"], p["lo"], p["hi"], vol["mean"], vol["lo"], vol["hi"],
         m3h["mean"], m3h["lo"], m3h["hi"], json.dumps(evidence_ids), reason, created_by, now()))
    return cur.lastrowid
