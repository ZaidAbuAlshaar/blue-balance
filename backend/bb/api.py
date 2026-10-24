"""FastAPI app. One origin serves the API, the processed data and (later) the built web app.

Run:  set PYTHONUTF8=1 && python -m uvicorn bb.api:app --host 127.0.0.1 --port 8000
"""
import hashlib
import json
import os
import secrets
import time

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bb import db
from bb.config import AGENT_MODEL, DB_PATH, EXTRACT_MODEL, OLLAMA_URL, PROCESSED, REPO
from bb.services import Services

SECRET = os.environ.get("BB_JWT_SECRET") or secrets.token_hex(32)
COOKIE = "bb_session"
SESSION_S = 8 * 3600

app = FastAPI(title="Blue Balance API", docs_url="/api/docs", openapi_url="/api/openapi.json")
con = db.connect(DB_PATH)
services = Services(con)


# ------------------------------------------------------------------ auth
class Login(BaseModel):
    user_id: str
    password: str


def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "login required")
    try:
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid session")
    return {"user_id": claims["sub"], "role": claims["role"], "display_name": claims["name"]}


def _result(payload):
    if isinstance(payload, dict) and payload.get("error") == "not_permitted":
        return JSONResponse(payload, status_code=403)
    if isinstance(payload, dict) and "error" in payload:
        return JSONResponse(payload, status_code=400)
    return payload


@app.post("/api/login")
def login(body: Login, response: Response):
    row = con.execute("SELECT * FROM users WHERE user_id = ?", (body.user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "wrong user or password")
    digest = hashlib.scrypt(body.password.encode(), salt=bytes.fromhex(row["salt"]), n=2**14, r=8, p=1).hex()
    if not secrets.compare_digest(digest, row["password_hash"]):
        db.audit(con, body.user_id, "user", "login_failed", None, {})
        con.commit()
        raise HTTPException(401, "wrong user or password")
    return _issue_session(response, row, "login")


def _issue_session(response, row, action):
    token = jwt.encode({"sub": row["user_id"], "role": row["role"], "name": row["display_name"],
                        "exp": int(time.time()) + SESSION_S}, SECRET, algorithm="HS256")
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=SESSION_S)
    db.audit(con, row["user_id"], "user", action, None, {})
    con.commit()
    return {"user_id": row["user_id"], "role": row["role"], "display_name": row["display_name"]}


# Demo role switch: pick a demo account from the top bar, no password. On by default for the
# hackathon demo; set BB_DEMO_SWITCH=0 to require /api/login. Roles are still enforced server-side.
DEMO_SWITCH = os.environ.get("BB_DEMO_SWITCH", "1") == "1"


class Switch(BaseModel):
    user_id: str


@app.get("/api/demo/users")
def demo_users():
    if not DEMO_SWITCH:
        raise HTTPException(404, "demo switch disabled")
    rows = con.execute("SELECT user_id, display_name, role FROM users ORDER BY role, user_id").fetchall()
    return {"label": "Simulated", "users": [dict(r) for r in rows]}


@app.post("/api/demo/switch")
def demo_switch(body: Switch, response: Response):
    if not DEMO_SWITCH:
        raise HTTPException(404, "demo switch disabled")
    row = con.execute("SELECT * FROM users WHERE user_id = ?", (body.user_id,)).fetchone()
    if row is None:
        raise HTTPException(400, "unknown demo user")
    return _issue_session(response, row, "demo_switch")


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return user


# ---------------------------------------------------------------- health
@app.get("/api/health")
def health():
    status = {"db": DB_PATH.exists(), "processed": {name: (PROCESSED / name).exists() for name in
              ("route.geojson", "fields.geojson", "segments.json", "field_timeseries.json")}}
    try:
        tags = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).json()
        names = {m["name"]: m["digest"][:12] for m in tags.get("models", [])}
        status["ollama"] = {"up": True, "agent_model": names.get(AGENT_MODEL), "extract_model": names.get(EXTRACT_MODEL)}
    except Exception:
        status["ollama"] = {"up": False}
    status["audit_chain"] = db.verify_audit_chain(con)
    return status


# ------------------------------------------------------- queue and cases
@app.get("/api/queue")
def queue(limit: int = 10, user=Depends(current_user)):
    return _result(services.get_priority_queue("KRK", limit, user))


@app.get("/api/cases/{case_id}")
def case(case_id: str, user=Depends(current_user)):
    return _result(services.query_posterior(case_id, user))


@app.get("/api/cases/{case_id}/explain")
def explain(case_id: str, user=Depends(current_user)):
    return _result(services.explain_ranking(case_id, user))


@app.get("/api/next-best")
def next_best(limit: int = 3, user=Depends(current_user)):
    return _result(services.propose_next_measurement("KRK", limit, user))


@app.get("/api/map/cases")
def map_cases(user=Depends(current_user)):
    return _result(services.map_layers(user))


@app.get("/api/map/route")
def map_route():
    return json.loads((PROCESSED / "route.geojson").read_text(encoding="utf-8"))


@app.get("/api/fields/{field_id}/timeseries")
def field_timeseries(field_id: str, user=Depends(current_user)):
    if user["role"] not in ("inspector", "engineer"):
        return JSONResponse({"error": "not_permitted"}, status_code=403)
    series = json.loads((PROCESSED / "field_timeseries.json").read_text(encoding="utf-8"))
    if field_id not in series:
        return JSONResponse({"error": "unknown_case_id"}, status_code=400)
    return {"field_id": field_id, "label": "Observed", "series": series[field_id]}


# ---------------------------------------------------------- field results
class FieldResult(BaseModel):
    case_id: str
    outcome: str
    note: str | None = Field(default=None, max_length=300)


@app.post("/api/field-results")
def field_result(body: FieldResult, user=Depends(current_user)):
    return _result(services.ingest_field_result(body.case_id, body.outcome, body.note, user))


# ------------------------------------------------------------ work orders
class WorkOrder(BaseModel):
    case_id: str
    task: str
    priority: str
    text_ar: str
    text_en: str
    crew_ar: str


@app.get("/api/work-orders")
def work_orders(user=Depends(current_user)):
    return _result(services.list_work_orders(user))


@app.post("/api/work-orders")
def create_work_order(body: WorkOrder, user=Depends(current_user)):
    return _result(services.create_work_order_draft(body.case_id, body.task, body.priority, body.text_ar,
                                                    body.text_en, body.crew_ar, user))


@app.post("/api/work-orders/{wo_id}/approve")
def approve_work_order(wo_id: str, user=Depends(current_user)):
    return _result(services.decide_work_order(wo_id, True, user))


@app.post("/api/work-orders/{wo_id}/reject")
def reject_work_order(wo_id: str, user=Depends(current_user)):
    return _result(services.decide_work_order(wo_id, False, user))


# --------------------------------------------------------------- map edits
class MapEdit(BaseModel):
    case_id: str
    kind: str
    geometry: dict
    evidence_ids: list[str]


class Decision(BaseModel):
    approve: bool
    reason: str | None = None


@app.get("/api/map-edits")
def map_edits(user=Depends(current_user)):
    return _result(services.list_map_edits(user))


@app.post("/api/map-edits")
def create_map_edit(body: MapEdit, user=Depends(current_user)):
    return _result(services.create_map_edit(body.case_id, body.kind, body.geometry, body.evidence_ids, user))


@app.post("/api/map-edits/{edit_id}/decide")
def decide_map_edit(edit_id: str, body: Decision, user=Depends(current_user)):
    return _result(services.decide_map_edit(edit_id, body.approve, body.reason, user))


@app.get("/api/map-edits/{edit_id}/export")
def export_map_edit(edit_id: str, crs: str = "EPSG:4326", user=Depends(current_user)):
    return _result(services.export_map_edit(edit_id, crs, user))


# ------------------------------------------------------------------- AI
class Ask(BaseModel):
    question: str = Field(max_length=1000)


@app.post("/api/agent/ask")
def ask(body: Ask, user=Depends(current_user)):
    from bb.agent.loop import run_agent
    agent_user = {**user, "via": "agent"}
    result = run_agent(body.question, agent_user, services)
    con.execute(
        "INSERT INTO agent_runs (user_id, question, answer, mode, tool_calls, evidence_ids, model, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (user["user_id"], body.question, result.get("answer", ""), result.get("mode", ""),
         json.dumps(result.get("tool_calls", []), ensure_ascii=False), json.dumps(result.get("evidence_ids", [])),
         result.get("model"), db.now()))
    db.audit(con, user["user_id"], "agent", "agent_ask", None,
             {"mode": result.get("mode"), "tools": [t.get("name") for t in result.get("tool_calls", [])]})
    con.commit()
    return result


class Report(BaseModel):
    text: str = Field(max_length=2000)
    use_llm: bool = True


@app.post("/api/reports/extract")
def extract(body: Report, user=Depends(current_user)):
    if user["role"] not in ("inspector", "engineer"):
        return JSONResponse({"error": "not_permitted"}, status_code=403)
    from bb.extract.extractor import extract_report
    return extract_report(body.text, use_llm=body.use_llm)


class ConfirmedReport(BaseModel):
    case_id: str | None = None
    text: str = Field(max_length=2000)
    fields: dict
    method: str
    flags: list = []


@app.post("/api/reports")
def submit_report(body: ConfirmedReport, user=Depends(current_user)):
    if user["role"] not in ("inspector", "engineer"):
        return JSONResponse({"error": "not_permitted"}, status_code=403)
    if any(isinstance(f, dict) and f.get("status") == "needs_confirmation" for f in body.fields.values()):
        return JSONResponse({"error": "fields_need_confirmation"}, status_code=400)
    report_id = "CR-" + secrets.token_hex(3).upper()
    con.execute("INSERT INTO crew_reports VALUES (?,?,?,?,?,?,?,?,?)",
                (report_id, body.case_id, body.text, json.dumps(body.fields, ensure_ascii=False), body.method,
                 json.dumps(body.flags, ensure_ascii=False), "Simulated", user["user_id"], db.now()))
    db.audit(con, user["user_id"], "user", "submit_crew_report", report_id, {"case_id": body.case_id})
    con.commit()
    return {"report_id": report_id, "label": "Simulated", "confirmed_by": user["user_id"]}


# -------------------------------------------------------- transparency/admin
@app.get("/api/transparency")
def transparency():
    return services.transparency()


@app.get("/api/audit")
def audit_log(user=Depends(current_user)):
    return _result(services.audit_log(user))




# ------------------------------------------------------------ demo views
from bb.config import SYNTHETIC  # noqa: E402
from bb.services import fusion_breakdown, impact  # noqa: E402


@app.get("/api/cases/{case_id}/fusion")
def case_fusion(case_id: str, user=Depends(current_user)):
    return _result(fusion_breakdown(services, case_id, user))


@app.get("/api/impact")
def impact_view(user=Depends(current_user)):
    return _result(impact(services, user))


@app.get("/api/fields/{field_id}/chips")
def field_chips(field_id: str, user=Depends(current_user)):
    if user["role"] not in ("inspector", "engineer"):
        return JSONResponse({"error": "not_permitted"}, status_code=403)
    years = [{"year": int(p.stem.rsplit("_", 1)[1]), "url": f"/chips/{p.name}"}
             for p in sorted((PROCESSED / "chips").glob(f"{field_id}_*.png"))]
    return {"field_id": field_id, "label": "Observed", "years": years}


@app.get("/api/demo/reports")
def demo_reports(user=Depends(current_user)):
    return json.loads((SYNTHETIC / "crew_reports_demo.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ static (must stay last: "/" catches everything)
if (PROCESSED / "chips").exists():
    app.mount("/chips", StaticFiles(directory=PROCESSED / "chips"), name="chips")
if (REPO / "web" / "dist").exists():
    app.mount("/", StaticFiles(directory=REPO / "web" / "dist", html=True), name="web")
