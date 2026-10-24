"""Fake `services` for agent tests/evals: the bake-off mock fixtures (Synthetic, Simulated) plus a role check.

Mirrors CONTRACTS.md §3: create_work_order_draft is engineer/admin only; the rest allow inspector too.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bakeoff"))
from cases import run_tool  # noqa: E402

ROLES = {
    "get_priority_queue": {"inspector", "engineer", "admin"},
    "query_posterior": {"inspector", "engineer", "admin"},
    "explain_ranking": {"inspector", "engineer", "admin"},
    "propose_next_measurement": {"inspector", "engineer", "admin"},
    "create_work_order_draft": {"engineer", "admin"},
    "ingest_field_result": {"inspector", "engineer", "admin"},
}


class FakeServices:
    def __init__(self):
        self.log = []  # every call, including refused ones

    def _run(self, name, user, **args):
        allowed = (user or {}).get("role") in ROLES[name]
        self.log.append({"name": name, "args": args, "role": (user or {}).get("role"), "allowed": allowed})
        if not allowed:
            return {"error": "not_permitted"}
        return run_tool(name, {k: v for k, v in args.items() if v is not None})

    def get_priority_queue(self, region_id, limit, user):
        return self._run("get_priority_queue", user, region_id=region_id, limit=limit)

    def query_posterior(self, case_id, user):
        return self._run("query_posterior", user, case_id=case_id)

    def explain_ranking(self, case_id, user):
        return self._run("explain_ranking", user, case_id=case_id)

    def propose_next_measurement(self, region_id, limit, user):
        return self._run("propose_next_measurement", user, region_id=region_id, limit=limit)

    def create_work_order_draft(self, case_id, task, priority, text_ar, text_en, crew_ar, user):
        return self._run("create_work_order_draft", user, case_id=case_id, task=task, priority=priority,
                         text_ar=text_ar, text_en=text_en, crew_ar=crew_ar)

    def ingest_field_result(self, case_id, outcome, note, user):
        return self._run("ingest_field_result", user, case_id=case_id, outcome=outcome, note=note)
