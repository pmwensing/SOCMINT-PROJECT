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

CASE_ID = "case-v24"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _portfolio() -> dict:
    links = {
        "case_review": f"/case-intelligence-review/{CASE_ID}",
        "dossier_assembly": f"/dossier-assembly/{CASE_ID}",
        "release_workspace": f"/dossier-release/{CASE_ID}",
        "closure_workspace": f"/case-closure/{CASE_ID}",
        "closure_history": f"/case-closure/{CASE_ID}/history",
        "delivery_workspace": f"/case-delivery?case_id={CASE_ID}",
    }
    case = {
        "case_id": CASE_ID,
        "stage": "closure_review",
        "status": "blocked",
        "blocked": True,
        "blockers": [{"key": "delivery_acknowledgement_required"}],
        "event_count": 4,
        "latest_action": "case_closure_readiness_review",
        "latest_actor": "manager",
        "latest_activity_at": "2026-06-16T00:00:00+00:00",
        "retention_disposition": None,
        "links": links,
    }
    return {
        "schema": "socmint.portfolio_operations_dashboard.v24_0",
        "version": "v24.0.0",
        "status": "ready",
        "counts": {"total": 1, "active": 1, "blocked": 1, "delivered": 0, "closed": 0, "archived": 0, "reopened": 0, "unstarted": 0},
        "stage_counts": {"closure_review": 1},
        "cases": [case],
        "blocked_cases": [case],
        "source_records_mutated": False,
        "portfolio_record_created": False,
        "next_action": "review_portfolio_operations",
    }


def _stage() -> dict:
    return {
        "schema": "socmint.portfolio_case_stage_overview.v24_1",
        "version": "v24.1.0",
        "status": "ready",
        "stage_model": ["unstarted", "active", "closure_review", "dossier_exported", "delivered", "closed", "retention_pending_archive", "archived", "reopened"],
        "stage_counts": {"closure_review": 1},
        "cases": [{
            "case_id": CASE_ID,
            "current_stage": "closure_review",
            "prior_stage": "active",
            "stage_entered_at": "2026-06-12T00:00:00+00:00",
            "stage_duration_seconds": 345600,
            "stage_duration_hours": 96.0,
            "progress_position": 3,
            "progress_total": 9,
            "progress_percent": 33.3,
            "blocked": True,
            "blocking_reason": "delivery_acknowledgement_required",
            "blockers": [{"key": "delivery_acknowledgement_required"}],
            "next_expected_action": "resolve_blocking_reason",
            "transitions": [],
            "latest_activity_at": "2026-06-16T00:00:00+00:00",
        }],
        "case_count": 1,
        "blocked_count": 1,
        "source_records_mutated": False,
        "stage_record_created": False,
        "next_action": "review_case_stage_overview",
    }


def _workload() -> dict:
    return {
        "schema": "socmint.portfolio_workload_assignment_monitoring.v24_2",
        "version": "v24.2.0",
        "status": "attention_required",
        "generated_at": "2026-06-16T01:00:00+00:00",
        "counts": {"total_decisions": 1, "active_workload": 1, "assigned_active": 1, "unassigned_active": 0, "reviewer_count": 1},
        "review_state_counts": {"unreviewed": 1},
        "reviewers": [{
            "reviewer": "alice", "total_assigned": 1, "active_workload": 1,
            "unreviewed": 1, "needs_follow_up": 0, "reviewed": 0, "accepted": 0,
            "oldest_assignment_age_hours": 72.0, "average_assignment_age_hours": 72.0,
            "reviewer_queue_href": "/case-intelligence-review/my-assignments",
            "supervisor_queue_href": "/case-intelligence-review/supervisor-queue?assigned_reviewer=alice",
            "workload_delta_from_average": 0.0, "workload_imbalanced": False, "overloaded": False,
        }],
        "entries": [{"case_id": CASE_ID, "review_state": "unreviewed", "assigned_reviewer": "alice", "assignment_age_hours": 72.0}],
        "unassigned_work": [],
        "workload_balance": {"minimum_active_workload": 1, "maximum_active_workload": 1, "average_active_workload": 1.0, "workload_spread": 0, "imbalanced": False, "overloaded_threshold": 2},
        "links": {"supervisor_queue": "/case-intelligence-review/supervisor-queue", "reviewer_queue": "/case-intelligence-review/my-assignments"},
        "source_assignments_mutated": False,
        "workload_record_created": False,
        "next_action": "monitor_reviewer_workload",
    }


def _blocked() -> dict:
    return {
        "schema": "socmint.portfolio_blocked_overdue_queue.v24_3",
        "version": "v24.3.0",
        "status": "attention_required",
        "thresholds": {"stage_overdue_hours": 72.0, "assignment_overdue_hours": 48.0},
        "counts": {"total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0, "blocked": 1, "stage_overdue": 1, "assignment_overdue": 1},
        "queue": [{
            "case_id": CASE_ID, "severity": "critical", "severity_rank": 4,
            "current_stage": "closure_review", "stage_age_hours": 96.0,
            "stage_overdue": True, "stage_overdue_by_hours": 24.0,
            "assignment_age_hours": 72.0, "assignment_overdue": True,
            "assignment_overdue_by_hours": 24.0, "blocked": True,
            "blocking_reason": "delivery_acknowledgement_required",
            "blockers": [{"key": "delivery_acknowledgement_required"}],
            "owner": "manager", "assigned_reviewers": ["alice"],
            "active_assignment_count": 1, "review_states": ["unreviewed"],
            "next_expected_action": "resolve_blocking_reason",
            "remediation_links": {
                "case_review": f"/case-intelligence-review/{CASE_ID}",
                "dossier_assembly": f"/dossier-assembly/{CASE_ID}",
                "closure_workspace": f"/case-closure/{CASE_ID}",
                "closure_history": f"/case-closure/{CASE_ID}/history",
                "supervisor_queue": f"/case-intelligence-review/supervisor-queue?case_id={CASE_ID}",
                "reviewer_queue": "/case-intelligence-review/my-assignments",
            },
        }],
        "source_records_mutated": False,
        "queue_record_created": False,
        "next_action": "remediate_highest_priority_case",
    }


def _escalations() -> dict:
    item = dict(_blocked()["queue"][0])
    item.update({"latest_control": None, "control_history_count": 0, "escalated": False, "acknowledged": False, "resolved": False})
    return {
        "schema": "socmint.portfolio_supervisor_escalation.v24_4",
        "version": "v24.4.0",
        "status": "attention_required",
        "items": [item],
        "item_count": 1,
        "source_records_mutated": False,
        "next_action": "review_supervisor_escalations",
    }


def _metrics() -> dict:
    duration = {stage: {"count": 0, "average_hours": None, "median_hours": None, "minimum_hours": None, "maximum_hours": None} for stage in _stage()["stage_model"]}
    duration["active"] = {"count": 1, "average_hours": 24.0, "median_hours": 24.0, "minimum_hours": 24.0, "maximum_hours": 24.0}
    return {
        "schema": "socmint.portfolio_operational_metrics.v24_5",
        "version": "v24.5.0",
        "status": "ready",
        "generated_at": "2026-06-16T01:00:00+00:00",
        "case_volume": {"total_cases": 1, "active_cases": 1, "completed_cases": 0, "blocked_cases": 1, "overdue_cases": 1},
        "completion_counts": {"delivered": 0, "closed": 0, "archived": 0, "reopened": 0},
        "stage_throughput": {"closure_review": 1},
        "current_stage_counts": {"closure_review": 1},
        "stage_duration_metrics": duration,
        "reviewer_throughput": [{"reviewer": "alice", "completed_reviews": 0, "active_workload": 1, "total_assigned": 1, "completion_rate_percent": 0.0, "average_assignment_age_hours": 72.0}],
        "rates": {"blocked_rate_percent": 100.0, "overdue_rate_percent": 100.0, "closure_archive_conversion_percent": 0.0, "reopen_rate_percent": 0.0},
        "trend_windows": [{"days": 7, "window_start": "2026-06-09T01:00:00+00:00", "window_end": "2026-06-16T01:00:00+00:00", "event_count": 4, "active_case_count": 1, "stage_throughput": {"closure_review": 1}, "closure_completions": 0, "archive_completions": 0, "reopen_completions": 0}],
        "source_records_mutated": False,
        "metrics_record_created": False,
        "next_action": "review_operational_metrics",
    }


def _history() -> dict:
    return {
        "schema": "socmint.portfolio_history_audit.v24_6",
        "version": "v24.6.0",
        "status": "ready",
        "generated_at": "2026-06-16T01:00:00+00:00",
        "history": [{"history_event_id": "checkpoint-1", "event_type": "metrics_checkpoint", "occurred_at": "2026-06-16T01:00:00+00:00", "actor": "system", "case_id": None, "source_action": None, "source_record_id": None, "source_binding_sha256": "a" * 64}],
        "event_count": 1,
        "event_type_counts": {"metrics_checkpoint": 1},
        "actor_counts": {"system": 1},
        "case_count": 1,
        "source_bound_event_count": 1,
        "current_portfolio_state": {"portfolio": {"status": "ready", "counts": {"total": 1}}},
        "current_portfolio_state_sha256": "b" * 64,
        "source_records_mutated": False,
        "history_record_created": False,
        "next_action": "review_portfolio_history",
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v24-browser-e2e-stable-secret-6f5e4d3c2b1a"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0
    from src.socmint import portfolio_operations_routes_v24_0 as routes
    from src.socmint import portfolio_supervisor_escalation_routes_v24_4 as page_routes

    routes.build_portfolio_operations_dashboard = _portfolio
    routes.build_case_status_stage_overview = _stage
    routes.build_workload_assignment_monitoring = _workload
    routes.build_blocked_overdue_case_queue = _blocked
    routes.build_escalation_control_state = _escalations
    routes.build_operational_metrics = _metrics
    routes.build_portfolio_history_audit = _history
    page_routes.build_escalation_control_state = _escalations

    control_ids = {"escalate": 1, "acknowledge": 2, "reassign": 3, "resolve": 4}
    for control in control_ids:
        setattr(routes, {
            "escalate": "record_escalation",
            "acknowledge": "acknowledge_escalation",
            "reassign": "reassign_escalation",
            "resolve": "resolve_escalation",
        }[control], lambda *args, _control=control, **kwargs: {
            "status": f"{_control}_recorded",
            "action_record_id": control_ids[_control],
            "source_records_mutated": False,
        })

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)
    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _fetch(browser, path: str, method: str = "GET", body: dict | None = None) -> dict:
    script = """
      const done = arguments[arguments.length - 1];
      fetch(arguments[0], {
        method: arguments[1], credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': 'v24-csrf'},
        body: arguments[1] === 'GET' ? undefined : JSON.stringify(arguments[2] || {})
      }).then(async r => done({status: r.status, data: await r.json()}))
        .catch(e => done({status: 0, data: {error: String(e)}}));
    """
    return browser.execute_async_script(script, path, method, body or {})


def run(output: Path) -> dict:
    report = {"schema": "socmint.portfolio_browser_e2e.v24_7", "version": "v24.7.0", "status": "passed", "checks": []}
    with tempfile.TemporaryDirectory(prefix="socmint-v24-") as temp:
        app = _app(Path(temp) / "v24.db")
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
        browser = webdriver.Chrome(options=options, service=ChromeService(driver_path) if driver_path else None)
        wait = WebDriverWait(browser, 20)
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            browser.get(base + "/")
            serializer = app.session_interface.get_signing_serializer(app)
            browser.add_cookie({"name": app.config.get("SESSION_COOKIE_NAME", "session"), "value": serializer.dumps({"user": "manager", "_csrf_token": "v24-csrf"}), "path": "/"})

            browser.get(base + "/portfolio-operations")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-portfolio-operations-dashboard]")))
            page = browser.page_source
            _check(report, "portfolio_dashboard", "Portfolio Operations Dashboard" in page)
            _check(report, "stage_overview", "Case Status and Stage Overview" in page)
            _check(report, "workload_monitoring", "Workload and Assignment Monitoring" in page)
            _check(report, "blocked_overdue_queue", "Blocked and Overdue Case Queue" in page)
            _check(report, "operational_metrics", "Operational Metrics and Throughput" in page)

            endpoints = [
                ("dashboard_api", "/api/v1/portfolio-operations", "status", "ready"),
                ("stage_api", "/api/v1/portfolio-operations/stage-overview", "case_count", 1),
                ("workload_api", "/api/v1/portfolio-operations/workload-monitoring", "status", "attention_required"),
                ("blocked_api", "/api/v1/portfolio-operations/blocked-overdue", "status", "attention_required"),
                ("metrics_api", "/api/v1/portfolio-operations/metrics", "status", "ready"),
            ]
            for key, path, field, expected in endpoints:
                result = _fetch(browser, path)
                _check(report, key, result["status"] == 200 and result["data"].get(field) == expected, json.dumps(result["data"], sort_keys=True))

            browser.get(base + "/portfolio-operations/escalations")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-portfolio-escalations]")))
            _check(report, "escalation_page", "Supervisor Escalation Controls" in browser.page_source)

            controls = [
                ("escalate", {"confirmed": True, "reason": "Critical overdue case"}),
                ("acknowledge", {"confirmed": True}),
                ("reassign", {"confirmed": True, "assigned_reviewer": "bob"}),
                ("resolve", {"confirmed": True, "resolution": "Remediated"}),
            ]
            for control, body in controls:
                result = _fetch(browser, f"/api/v1/portfolio-operations/{CASE_ID}/{control}", "POST", body)
                _check(report, f"control_{control}", result["status"] == 200 and result["data"].get("status") == f"{control}_recorded", json.dumps(result["data"], sort_keys=True))

            browser.get(base + "/portfolio-operations/history")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-portfolio-history-audit]")))
            _check(report, "portfolio_history_page", "Ordered Operational History" in browser.page_source)
            history = _fetch(browser, "/api/v1/portfolio-operations/history")
            _check(report, "portfolio_history_api", history["status"] == 200 and history["data"].get("status") == "ready")

            checkpoint = _fetch(browser, "/api/v1/portfolio-operations/product-review-checkpoint")
            _check(report, "product_checkpoint", checkpoint["status"] == 200 and checkpoint["data"].get("ready") is True, json.dumps(checkpoint["data"], sort_keys=True))
        except Exception as exc:
            _check(report, "browser_exception", False, f"{type(exc).__name__}: {exc}")
        finally:
            browser.quit()
            server.shutdown()

    report["passed_count"] = sum(1 for item in report["checks"] if item["ok"])
    report["failed_count"] = sum(1 for item in report["checks"] if not item["ok"])
    report["status"] = "passed" if report["failed_count"] == 0 else "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/v24_7_portfolio_browser_e2e.json"))
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
