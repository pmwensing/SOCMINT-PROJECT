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

from selenium import webdriver  # noqa: E402
from selenium.webdriver.chrome.service import Service as ChromeService  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

CASE_ID = "case-v23"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _workspace(state: dict) -> dict:
    return {
        "case_id": CASE_ID,
        "status": "eligible_for_closure_review",
        "current_release_outcome": "delivered_and_acknowledged",
        "closure_eligible": True,
        "archive_ready": True,
        "blocker_count": 0,
        "blockers": [],
        "release_history": {
            "closure_summary": {"case_id": CASE_ID, "closure_ready": True}
        },
        "delivery_recovery_state": {
            "delivery_failed": False,
            "delivery_succeeded": True,
            "acknowledgement_received": True,
            "next_action": "monitor_delivery_recovery",
        },
        "retention_policies": [
            {
                "policy_id": "standard_case_retention",
                "display_name": "Standard case retention",
                "retention_years": 7,
                "archive_class": "standard",
                "description": "Seven-year case retention.",
            }
        ],
        "proposed_retention_policy": {
            "policy_id": "standard_case_retention",
            "display_name": "Standard case retention",
            "retention_years": 7,
            "archive_class": "standard",
            "description": "Seven-year case retention.",
        },
        "supervisor_actions": [],
        "links": {
            "release_workspace": f"/dossier-release/{CASE_ID}",
            "release_history": f"/dossier-release/{CASE_ID}/history",
            "case_delivery_workspace": f"/case-delivery?case_id={CASE_ID}",
        },
        "latest_readiness_review": state.get("readiness"),
        "latest_closure_decision": state.get("closure"),
        "latest_retention_assignment": state.get("retention"),
        "latest_archive_package": state.get("archive"),
    }


def _history(state: dict) -> dict:
    timeline = state["timeline"]
    reopened = bool(state.get("authorization", {}).get("case_reopened"))
    return {
        "schema": "socmint.case_closure_archive_history.v23_6",
        "version": "v23.6.0",
        "case_id": CASE_ID,
        "status": "complete",
        "timeline": timeline,
        "event_count": len(timeline),
        "current_closure_state": "reopened" if reopened else "closed",
        "current_archive_state": "generated",
        "retention_disposition": (state.get("retention") or {}).get("disposition"),
        "reopen_status": "authorized" if reopened else "none",
        "unresolved_actions": [],
        "unresolved_action_count": 0,
        "latest_events": {},
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": "product_review_checkpoint",
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v23-browser-e2e-stable-secret-8d7c6b5a4f3e2d1c"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import (
        register_dossier_assembly_routes_v21_0,
    )
    from src.socmint import case_closure_routes_v23_0 as closure_routes
    from src.socmint import case_reopen_routes_v23_5 as reopen_routes
    from src.socmint import case_closure_history_routes_v23_6 as history_routes

    state: dict = {"timeline": []}

    closure_routes.build_case_closure_workspace = lambda case_id: _workspace(state)
    closure_routes.latest_closure_readiness_review = lambda case_id: state.get(
        "readiness"
    )
    closure_routes.latest_supervisor_closure_decision = lambda case_id: state.get(
        "closure"
    )
    closure_routes.latest_retention_assignment = lambda case_id: state.get("retention")
    closure_routes.latest_case_archive_package = lambda case_id: state.get("archive")

    def readiness(*args, **kwargs):
        value = {
            "status": "review_recorded",
            "decision": "ready",
            "review_id": "review-v23",
            "review_sha256": "1" * 64,
            "reviewed_by": "supervisor",
            "reviewed_at": "2026-06-15T00:01:00",
            "ready_for_supervisor_closure_decision": True,
        }
        state["readiness"] = value
        state["timeline"].append(
            {
                "timeline_id": 1,
                "event_type": "readiness_review",
                "actor": "supervisor",
                "occurred_at": value["reviewed_at"],
                "details": value,
            }
        )
        return value

    def closure(*args, **kwargs):
        value = {
            "status": "closure_decision_recorded",
            "decision": "close",
            "closure_decision_id": "closure-v23",
            "closure_decision_sha256": "2" * 64,
            "decided_by": "supervisor",
            "decided_at": "2026-06-15T00:02:00",
            "case_closed": True,
            "ready_for_retention_assignment": True,
        }
        state["closure"] = value
        state["timeline"].append(
            {
                "timeline_id": 2,
                "event_type": "closure_decision",
                "actor": "supervisor",
                "occurred_at": value["decided_at"],
                "details": value,
            }
        )
        return value

    def retention(*args, **kwargs):
        value = {
            "status": "retention_assignment_recorded",
            "retention_assignment_id": "retention-v23",
            "policy": {"display_name": "Standard case retention"},
            "disposition": {
                "disposition": "retain_until_expiration",
                "archive_class": "standard",
                "retention_years": 7,
                "retention_expires_at": "2033-06-15T00:02:00",
                "legal_hold": False,
            },
            "assigned_by": "supervisor",
            "assigned_at": "2026-06-15T00:03:00",
            "ready_for_archive_package": True,
        }
        state["retention"] = value
        state["timeline"].append(
            {
                "timeline_id": 3,
                "event_type": "retention_assignment",
                "actor": "supervisor",
                "occurred_at": value["assigned_at"],
                "details": value,
            }
        )
        return value

    def archive(*args, **kwargs):
        value = {
            "status": "archive_package_generated",
            "archive_record_id": 4,
            "archive_package_id": "archive-v23",
            "archive_package_sha256": "3" * 64,
            "generated_by": "supervisor",
            "generated_at": "2026-06-15T00:04:00",
            "components": {"audit_references": []},
        }
        state["archive"] = value
        state["timeline"].append(
            {
                "timeline_id": 4,
                "event_type": "archive_generation",
                "actor": "supervisor",
                "occurred_at": value["generated_at"],
                "details": value,
            }
        )
        return value

    def request_reopen(*args, **kwargs):
        value = {
            "status": "reopen_request_recorded",
            "request_record_id": 5,
            "reopen_request_id": "request-v23",
            "reopen_request_sha256": "4" * 64,
            "requested_by": "supervisor",
            "requested_at": "2026-06-15T00:05:00",
            "case_reopened": False,
        }
        state["request"] = value
        state["timeline"].append(
            {
                "timeline_id": 5,
                "event_type": "reopen_request",
                "actor": "supervisor",
                "occurred_at": value["requested_at"],
                "details": value,
            }
        )
        return value

    def authorize(*args, **kwargs):
        value = {
            "status": "reopen_authorization_recorded",
            "authorization_record_id": 6,
            "reopen_authorization_id": "authorization-v23",
            "decision": "authorize",
            "authorized_by": "supervisor",
            "authorized_at": "2026-06-15T00:06:00",
            "case_reopened": True,
        }
        state["authorization"] = value
        state["timeline"].append(
            {
                "timeline_id": 6,
                "event_type": "reopen_authorization",
                "actor": "supervisor",
                "occurred_at": value["authorized_at"],
                "details": value,
            }
        )
        return value

    closure_routes.review_case_closure_readiness = readiness
    closure_routes.record_supervisor_closure_decision = closure
    closure_routes.assign_retention_policy = retention
    closure_routes.generate_case_archive_package = archive
    reopen_routes.create_reopen_request = request_reopen
    reopen_routes.authorize_reopen_request = authorize
    reopen_routes.latest_reopen_request = lambda case_id: state.get("request")
    reopen_routes.latest_reopen_authorization = lambda case_id: state.get(
        "authorization"
    )
    history_routes.build_case_closure_history = lambda case_id: _history(state)

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _fetch(browser, path: str, method: str = "GET", body: dict | None = None) -> dict:
    script = """
      const done = arguments[arguments.length - 1];
      const path = arguments[0], method = arguments[1], body = arguments[2];
      fetch(path, {
        method,
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': 'v23-csrf'},
        body: method === 'GET' ? undefined : JSON.stringify(body || {})
      }).then(async r => done({status: r.status, data: await r.json()}))
        .catch(e => done({status: 0, data: {error: String(e)}}));
    """
    return browser.execute_async_script(script, path, method, body or {})


def run(output: Path) -> dict:
    report = {
        "schema": "socmint.case_closure_browser_e2e.v23_7",
        "version": "v23.7.0",
        "status": "passed",
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="socmint-v23-") as temp:
        app = _app(Path(temp) / "v23.db")
        server = make_server("127.0.0.1", _port(), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        chromium = shutil.which("chromium") or shutil.which("google-chrome")
        if chromium:
            options.binary_location = chromium
        driver_path = shutil.which("chromedriver")
        browser = webdriver.Chrome(
            options=options, service=ChromeService(driver_path) if driver_path else None
        )
        wait = WebDriverWait(browser, 20)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie(
                {
                    "name": app.config.get("SESSION_COOKIE_NAME", "session"),
                    "value": serializer.dumps(
                        {"user": "supervisor", "_csrf_token": "v23-csrf"}
                    ),
                    "path": "/",
                }
            )
            browser.get(base + f"/case-closure/{CASE_ID}")
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-case-closure-workspace]")
                )
            )
            _check(report, "closure_workspace_render", True)

            steps = [
                (
                    "closure_readiness",
                    f"/api/v1/case-closure/{CASE_ID}/readiness-review",
                    {"decision": "ready", "confirmed": True},
                ),
                (
                    "supervisor_closure_decision",
                    f"/api/v1/case-closure/{CASE_ID}/closure-decision",
                    {"decision": "close", "confirmed": True},
                ),
                (
                    "retention_assignment",
                    f"/api/v1/case-closure/{CASE_ID}/retention-assignment",
                    {"policy_id": "standard_case_retention", "confirmed": True},
                ),
                (
                    "archive_generation",
                    f"/api/v1/case-closure/{CASE_ID}/archive-package",
                    {},
                ),
                (
                    "reopen_request",
                    f"/api/v1/case-closure/{CASE_ID}/reopen-request",
                    {"reason": "New evidence", "confirmed": True},
                ),
                (
                    "reopen_authorization",
                    f"/api/v1/case-closure/{CASE_ID}/reopen-authorization",
                    {"decision": "authorize", "confirmed": True},
                ),
            ]
            for key, path, body in steps:
                result = _fetch(browser, path, "POST", body)
                _check(
                    report,
                    key,
                    result["status"] == 200,
                    json.dumps(result["data"], sort_keys=True),
                )

            browser.get(base + f"/case-closure/{CASE_ID}/history")
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-case-closure-history]")
                )
            )
            _check(
                report,
                "consolidated_history",
                "Ordered Case Timeline" in browser.page_source,
            )
            history = _fetch(browser, f"/api/v1/case-closure/{CASE_ID}/history")
            _check(
                report,
                "closure_state_reopened",
                history["data"].get("current_closure_state") == "reopened",
            )
            _check(
                report,
                "archive_state_generated",
                history["data"].get("current_archive_state") == "generated",
            )
            _check(
                report,
                "closure_history_complete",
                history["data"].get("status") == "complete",
            )
            checkpoint = _fetch(
                browser, "/api/v1/case-closure/product-review-checkpoint"
            )
            _check(
                report,
                "product_checkpoint",
                checkpoint["status"] == 200 and checkpoint["data"].get("ready") is True,
                json.dumps(checkpoint["data"], sort_keys=True),
            )
        except Exception as exc:
            _check(report, "browser_exception", False, f"{type(exc).__name__}: {exc}")
        finally:
            browser.quit()
            server.shutdown()

    report["passed_count"] = sum(1 for item in report["checks"] if item["ok"])
    report["failed_count"] = sum(1 for item in report["checks"] if not item["ok"])
    report["status"] = "passed" if report["failed_count"] == 0 else "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/v23_7_case_closure_browser_e2e.json"),
    )
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
