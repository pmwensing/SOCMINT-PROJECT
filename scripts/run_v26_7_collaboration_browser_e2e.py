from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import redirect, session  # noqa: E402
from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

CASE_ID = "case-alpha"
USER = "e2e-analyst"
CSRF = "v26-e2e-csrf"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workspace() -> dict:
    return {
        "schema": "socmint.collaboration_workspace.v26_0", "version": "v26.0.0",
        "status": "ready", "user_identity": USER,
        "participating_cases": [{"case_id": CASE_ID, "assigned_roles": ["lead_analyst"]}],
        "active_collaborators": [{"case_id": CASE_ID, "user_identity": USER}],
        "pending_requests": [], "pending_handoffs": [], "unread_updates": [],
        "unresolved_review_requests": [], "blocked_collaboration_items": [],
        "unresolved_collaboration_actions": [],
        "access_scope": {"mode": "restricted", "allowed_case_ids": [CASE_ID]},
        "read_only": True, "source_records_mutated": False,
    }


def _team() -> dict:
    return {"schema": "socmint.case_team_role_assignment.v26_1", "version": "v26.1.0", "status": "ready", "case_id": CASE_ID, "role_catalog": ["case_owner", "lead_analyst", "analyst", "reviewer", "supervisor", "evidence_custodian", "observer"], "current_assignments": [], "active_assignments": [], "active_assignment_count": 0, "history": [], "history_count": 0, "source_records_mutated": False, "read_only_view_created_record": False, "case_access_scope_changed": False}


def _notes() -> dict:
    return {"schema": "socmint.collaboration_notes_mentions.v26_2", "version": "v26.2.0", "status": "ready", "case_id": CASE_ID, "user_identity": USER, "target_types": ["case"], "visibility_scopes": ["case_team"], "priorities": ["normal"], "notes": [], "active_notes": [], "active_note_count": 0, "unread_mentions": [], "unread_mention_count": 0, "acknowledgement_required": [], "acknowledgement_required_count": 0, "history": [], "history_count": 0, "source_records_mutated": False, "access_granted_by_mention": False}


def _requests() -> dict:
    return {"schema": "socmint.collaboration_requests_handoffs.v26_3", "version": "v26.3.0", "status": "ready", "case_id": CASE_ID, "request_types": ["evidence_review"], "handoff_types": ["review_task"], "priorities": ["normal"], "requests": [], "handoffs": [], "pending_requests": [], "pending_handoffs": [], "counts": {"requests": 0, "handoffs": 0, "pending_requests": 0, "pending_handoffs": 0}, "history": [], "source_records_mutated": False}


def _responses() -> dict:
    return {"schema": "socmint.collaboration_responses_resolution.v26_4", "version": "v26.4.0", "status": "ready", "case_id": CASE_ID, "response_types": ["acknowledgement", "acceptance", "decline", "response_note", "completion", "escalation", "resolution"], "target_types": ["note", "request", "handoff"], "latest_responses": [], "unresolved_responses": [], "counts": {"history": 0, "targets": 0, "unresolved": 0, "resolved": 0}, "history": [], "source_records_mutated": False}


def _queue() -> dict:
    return {"schema": "socmint.team_workload_collaboration_queue.v26_5", "version": "v26.5.0", "status": "ready", "user_identity": USER, "my_assigned_cases": [], "pending_requests": [], "awaiting_acknowledgement": [], "delegated_by_me": [], "pending_handoffs": [], "overdue_items": [], "unassigned_work": [], "supervisor_escalations": [], "recent_activity": [], "collaboration_load_by_user": [], "workload_imbalance": [], "counts": {}, "average_collaboration_load": 0.0, "access_scope": {"mode": "restricted", "allowed_case_ids": [CASE_ID]}, "queue_sha256": "q" * 64, "read_only": True}


def _history() -> dict:
    return {"schema": "socmint.collaboration_history_audit.v26_6", "version": "v26.6.0", "status": "ready", "generated_at": "2026-06-16T22:00:00+00:00", "user_identity": USER, "access_scope": {"mode": "restricted", "allowed_case_ids": [CASE_ID]}, "history": [], "event_count": 0, "event_type_counts": {}, "actor_counts": {}, "case_count": 1, "source_bound_event_count": 0, "current_collaboration_state": {"active_team": [], "current_owner": None, "open_requests": [], "pending_handoffs": [], "unacknowledged_items": [], "overdue_items": [], "unresolved_responses": [], "active_escalations": [], "unresolved_actions": {}}, "current_collaboration_state_sha256": "h" * 64, "source_records_mutated": False, "history_record_created": False}


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v26-browser-e2e-stable-secret-key-32chars-minimum"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0
    from src.socmint import collaboration_routes_v26_0 as root_routes
    from src.socmint import case_team_role_assignment_routes_v26_1 as team_routes
    from src.socmint import collaboration_notes_routes_v26_2 as note_routes
    from src.socmint import collaboration_requests_handoffs_routes_v26_3 as request_routes
    from src.socmint import collaboration_responses_resolution_routes_v26_4 as response_routes
    from src.socmint import team_workload_collaboration_queue_routes_v26_5 as queue_routes
    from src.socmint import collaboration_history_audit_routes_v26_6 as history_routes

    root_routes.build_collaboration_workspace = lambda *a, **k: _workspace()
    team_routes.build_case_team_workspace = lambda case_id: _team()
    team_routes.assign_case_team_role = lambda *a, **k: {"status": "case_team_assignment_recorded", "case_team_assignment_id": "assignment-e2e"}
    note_routes.build_collaboration_notes_workspace = lambda *a, **k: _notes()
    note_routes.create_note = lambda *a, **k: {"status": "collaboration_note_recorded", "collaboration_note_id": "note-e2e"}
    request_routes.build_workspace = lambda case_id: _requests()
    request_routes.create_request = lambda *a, **k: {"status": "collaboration_request_recorded", "collaboration_request_id": "request-e2e"}
    request_routes.create_handoff = lambda *a, **k: {"status": "collaboration_handoff_recorded", "collaboration_handoff_id": "handoff-e2e"}
    response_routes.build_collaboration_response_workspace = lambda case_id: _responses()
    response_routes.record_collaboration_response = lambda *a, **k: {"status": "collaboration_response_recorded", "collaboration_response_id": "response-e2e"}
    queue_routes.build_team_workload_collaboration_queue = lambda *a, **k: _queue()
    history_routes.build_collaboration_history_audit = lambda *a, **k: _history()

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)

    @app.get("/_v26_e2e_login")
    def _v26_e2e_login():
        session["user"] = USER
        session["allowed_case_ids"] = [CASE_ID]
        session["_csrf_token"] = CSRF
        return redirect("/collaboration")

    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _post(driver, url: str, payload: dict) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        fetch(arguments[0], {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRF-Token':'v26-e2e-csrf'}, body:JSON.stringify(arguments[1])})
          .then(async r => done({status:r.status, body:await r.json()}))
          .catch(e => done({status:0, body:{error:String(e)}}));
        """, url, payload,
    )


def run() -> dict:
    report = {"schema": "socmint.collaboration_browser_e2e.v26_7", "version": "v26.7.0", "checks": []}
    temp = Path(tempfile.mkdtemp(prefix="socmint-v26-e2e-"))
    port = _port()
    server = make_server("127.0.0.1", port, _app(temp / "e2e.db"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        binary = os.getenv("SOCMINT_CHROME_BINARY") or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        executable = os.getenv("SOCMINT_CHROMEDRIVER") or shutil.which("chromedriver")
        if binary:
            options.binary_location = binary
        driver = webdriver.Chrome(service=ChromeService(executable_path=executable) if executable else ChromeService(), options=options)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v26_e2e_login")
        pages = [
            ("workspace_page", "/collaboration", "Collaboration"),
            ("team_page", f"/cases/{CASE_ID}/team", "Case Team"),
            ("notes_page", f"/cases/{CASE_ID}/collaboration-notes", "Collaboration Notes"),
            ("requests_page", f"/cases/{CASE_ID}/collaboration-requests", "Review Requests"),
            ("responses_page", f"/cases/{CASE_ID}/collaboration-responses", "Responses"),
            ("queue_page", "/collaboration/my-work", "Team Workload"),
            ("history_page", "/collaboration/history", "Collaboration History"),
            ("checkpoint_page", "/collaboration/product-review", "Product Review"),
        ]
        for key, path, phrase in pages:
            driver.get(base + path)
            _check(report, key, phrase.lower() in driver.page_source.lower())

        posts = [
            ("team_assignment_post", f"/api/v1/cases/{CASE_ID}/team/assignments", {"user_identity":"analyst-b","role":"reviewer","reason":"E2E assignment","confirmed":True}),
            ("note_post", f"/api/v1/cases/{CASE_ID}/collaboration-notes", {"body":"E2E collaboration note","target_type":"case","mentioned_users":["analyst-b"],"visibility":"case_team","priority":"normal","acknowledgement_required":True,"confirmed":True}),
            ("request_post", f"/api/v1/cases/{CASE_ID}/collaboration-requests", {"requested_from":"analyst-b","request_type":"evidence_review","reason":"E2E review","priority":"normal","confirmed":True}),
            ("handoff_post", f"/api/v1/cases/{CASE_ID}/collaboration-handoffs", {"handoff_to":"analyst-b","handoff_type":"review_task","reason":"E2E handoff","priority":"normal","confirmed":True}),
            ("response_post", f"/api/v1/cases/{CASE_ID}/collaboration-responses", {"target_type":"request","target_id":"request-e2e","response_type":"acknowledgement","reason":"E2E acknowledgement","confirmed":True}),
        ]
        for key, path, payload in posts:
            result = _post(driver, base + path, payload)
            _check(report, key, result.get("status") == 200, json.dumps(result))

        apis = [
            "/api/v1/collaboration", f"/api/v1/cases/{CASE_ID}/team",
            f"/api/v1/cases/{CASE_ID}/collaboration-notes",
            f"/api/v1/cases/{CASE_ID}/collaboration-requests",
            f"/api/v1/cases/{CASE_ID}/collaboration-responses",
            "/api/v1/collaboration/my-work", "/api/v1/collaboration/history",
            "/api/v1/collaboration/product-review-checkpoint",
        ]
        for path in apis:
            driver.get(base + path)
            _check(report, "api_" + path.rsplit("/", 1)[-1], "schema" in driver.page_source or "ready" in driver.page_source)
    except Exception as exc:
        _check(report, "browser_exception", False, repr(exc))
    finally:
        if driver:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp, ignore_errors=True)

    report["passed_count"] = sum(1 for item in report["checks"] if item["ok"])
    report["failed_count"] = sum(1 for item in report["checks"] if not item["ok"])
    report["status"] = "passed" if report["failed_count"] == 0 else "failed"
    report["v26_closed"] = report["status"] == "passed"
    report["next_action"] = "begin_v27" if report["v26_closed"] else "resolve_v26_browser_e2e_failures"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
