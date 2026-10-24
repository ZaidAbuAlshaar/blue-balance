"""HTTP-level checks: login, role gating, live re-rank, approval by a second engineer."""
import json
import os

import pytest


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("api") / "api.sqlite"
    os.environ["BB_DB"] = str(db_path)
    import importlib
    import bb.config
    importlib.reload(bb.config)
    import bb.seed
    importlib.reload(bb.seed)
    bb.seed.seed(db_path)
    import bb.api
    importlib.reload(bb.api)
    from fastapi.testclient import TestClient
    return TestClient(bb.api.app)


def _password(user_id):
    from bb.config import SYNTHETIC
    users = json.loads((SYNTHETIC / "demo_users.json").read_text(encoding="utf-8"))["users"]
    return next(u["password"] for u in users if u["user_id"] == user_id)


def _login(client, user_id):
    client.cookies.clear()
    r = client.post("/api/login", json={"user_id": user_id, "password": _password(user_id)})
    assert r.status_code == 200, r.text
    return r.json()


def test_login_required(client):
    client.cookies.clear()
    assert client.get("/api/queue").status_code == 401


def test_wrong_password_rejected(client):
    client.cookies.clear()
    assert client.post("/api/login", json={"user_id": "eng_a", "password": "nope"}).status_code == 401


def test_admin_cannot_see_sensitive_layers(client):
    _login(client, "admin_1")
    assert client.get("/api/map/cases").status_code == 403
    assert client.get("/api/audit").status_code == 200


def test_inspector_queue_and_live_rerank(client):
    _login(client, "insp_1")
    queue = client.get("/api/queue").json()["queue"]
    top = queue[0]
    assert set(top["m3_per_insp_hour"]) == {"mean", "lo", "hi"}
    r = client.post("/api/field-results", json={"case_id": top["case_id"], "outcome": "no_anomaly_found"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["posterior_after"] < body["posterior_before"]
    assert body["label"] == "Simulated"


def test_work_order_needs_second_engineer(client):
    _login(client, "eng_a")
    case_id = client.get("/api/queue").json()["queue"][0]["case_id"]
    wo = client.post("/api/work-orders", json={"case_id": case_id, "task": "inspect_connection", "priority": "high",
                                              "text_ar": "فحص", "text_en": "Inspect", "crew_ar": "افحصوا"}).json()
    assert client.post(f"/api/work-orders/{wo['wo_id']}/approve").status_code == 403
    _login(client, "eng_b")
    assert client.post(f"/api/work-orders/{wo['wo_id']}/approve").json()["status"] == "approved"


def test_health_and_transparency(client):
    health = client.get("/api/health").json()
    assert health["audit_chain"]["ok"] is True
    assert all(health["processed"].values())
    labels = client.get("/api/transparency").json()["evidence_by_label"]
    assert labels.get("Field-verified", 0) == 0
