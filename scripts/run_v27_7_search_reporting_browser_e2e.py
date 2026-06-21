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

USER = "e2e-analyst"
CASE_ID = "case-alpha"
CSRF = "v27-e2e-csrf"
VIEW_ID = "saved-view-e2e"
WATCHLIST_ID = "watchlist-e2e"
REPORT_ID = "report-e2e"


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _access() -> dict:
    return {"mode": "restricted", "allowed_case_ids": [CASE_ID]}


def _result() -> dict:
    return {
        "result_id": "result-e2e",
        "record_type": "finding",
        "result_type": "finding",
        "case_id": CASE_ID,
        "score": 100.0,
        "title": "E2E Finding",
        "summary": "E2E summary",
        "actor": USER,
        "status": "open",
        "occurred_at": "2026-06-17T22:00:00+00:00",
        "matched_terms": ["e2e"],
        "field_matches": [],
        "preview": {"fields": [], "field_count": 0, "matched_field_count": 0},
        "links": {
            "primary": f"/case-intelligence-review/{CASE_ID}",
            "case": f"/case-intelligence-review/{CASE_ID}",
            "evidence": f"/dossier-assembly/{CASE_ID}",
        },
    }


def _global() -> dict:
    return {
        "schema": "socmint.global_investigation_search.v27_0",
        "version": "v27.0.0",
        "status": "ready",
        "query": "e2e",
        "query_contract": {"limit": 100},
        "result_count": 1,
        "visible_case_ids": [CASE_ID],
        "access_scope": _access(),
        "search_sha256": "a" * 64,
        "result_type_counts": {"finding": 1},
        "results": [_result()],
    }


def _core() -> dict:
    return {
        "schema": "socmint.core_record_search.v27_1",
        "version": "v27.1.0",
        "status": "ready",
        "query": "e2e",
        "record_types": ["case", "entity", "evidence", "finding"],
        "applied_filters": {
            "record_types": [],
            "case_ids": [],
            "actors": [],
            "statuses": [],
            "limit": 100,
        },
        "facets": {"record_type": {"finding": 1}},
        "result_count": 1,
        "visible_case_ids": [CASE_ID],
        "search_sha256": "b" * 64,
        "results": [_result()],
    }


def _advanced() -> dict:
    return {
        "schema": "socmint.advanced_search_filters.v27_2",
        "version": "v27.2.0",
        "status": "ready",
        "query": "e2e",
        "sort_modes": ["relevance", "newest", "oldest", "case", "type", "actor"],
        "active_filters": {
            "record_types": [],
            "case_ids": [],
            "actors": [],
            "statuses": [],
            "stages": [],
            "source_actions": [],
            "confidences": [],
            "priorities": [],
            "date_from": "",
            "date_to": "",
            "include_terms": [],
            "exclude_terms": [],
            "exact_fields": {},
            "sort": "relevance",
            "limit": 100,
        },
        "active_filter_count": 0,
        "candidate_count": 1,
        "result_count": 1,
        "filter_sha256": "c" * 64,
        "result_set_sha256": "d" * 64,
        "facets": {"record_type": {"finding": 1}},
        "filtered_facets": {"record_type": {"finding": 1}},
        "excluded_counts": {},
        "results": [_result()],
        "access_scope": _access(),
    }


def _view() -> dict:
    return {
        "saved_view_id": VIEW_ID,
        "name": "E2E View",
        "owner": USER,
        "visibility": "private",
        "revision": 1,
        "view_status": "active",
        "definition": {"query": "e2e", "filters": {}},
        "definition_sha256": "e" * 64,
        "saved_view_event_id": "view-event-e2e",
        "saved_view_event_sha256": "f" * 64,
    }


def _saved() -> dict:
    return {
        "schema": "socmint.saved_search_views.v27_3",
        "version": "v27.3.0",
        "status": "ready",
        "user_identity": USER,
        "visibilities": ["private", "shared"],
        "saved_views": [_view()],
        "active_saved_views": [_view()],
        "owned_saved_views": [_view()],
        "shared_saved_views": [],
        "saved_view_count": 1,
        "active_saved_view_count": 1,
        "owned_saved_view_count": 1,
        "shared_saved_view_count": 0,
        "history_count": 1,
    }


def _watchlist() -> dict:
    return {
        "watchlist_id": WATCHLIST_ID,
        "name": "E2E Watchlist",
        "owner": USER,
        "watchlist_status": "active",
        "cadence": "daily",
        "notification_rule": "any_change",
        "saved_view_binding": {"saved_view_id": VIEW_ID},
        "last_run_at": None,
        "next_due_at": None,
    }


def _watchlists() -> dict:
    return {
        "schema": "socmint.watchlist_monitoring.v27_4",
        "version": "v27.4.0",
        "status": "ready",
        "user_identity": USER,
        "watchlists": [_watchlist()],
        "watchlist_count": 1,
        "active_watchlist_count": 1,
        "paused_watchlist_count": 0,
        "due_watchlist_count": 0,
        "notification_pending_count": 0,
        "monitoring_run_count": 0,
    }


def _report() -> dict:
    return {
        "report_id": REPORT_ID,
        "name": "E2E Report",
        "owner": USER,
        "visibility": "private",
        "revision": 1,
        "report_status": "active",
        "definition": {
            "description": "E2E",
            "sections": [{"section_type": "text", "title": "Notes", "text": "E2E"}],
            "export_formats": ["json", "csv", "html"],
        },
        "definition_sha256": "g" * 64,
        "report_event_id": "report-event-e2e",
        "report_event_sha256": "h" * 64,
    }


def _reports() -> dict:
    return {
        "schema": "socmint.report_builder_export_packages.v27_5",
        "version": "v27.5.0",
        "status": "ready",
        "reports": [_report()],
        "report_count": 1,
        "packages": [],
        "package_count": 0,
    }


def _history() -> dict:
    event = {
        "history_event_id": "v27-history-1",
        "family": "saved_view",
        "source_action": "saved_search_view_created",
        "event_type": "created",
        "actor": USER,
        "occurred_at": "2026-06-17T22:00:00+00:00",
        "identifiers": {"saved_view_id": VIEW_ID},
        "event_counts": {
            "section_count": None,
            "result_count": None,
            "added_count": None,
            "removed_count": None,
        },
        "hashes": {"definition_sha256": "e" * 64},
        "direct_links": {
            "saved_views": "/global-search/saved-views",
            "watchlists": "/global-search/watchlists",
            "reports": "/global-search/reports",
            "advanced_search": "/global-search/advanced",
        },
    }
    return {
        "schema": "socmint.search_reporting_history_audit.v27_6",
        "version": "v27.6.0",
        "status": "ready",
        "events": [event],
        "event_count": 1,
        "family_counts": {"saved_view": 1},
        "action_counts": {"saved_search_view_created": 1},
        "actor_counts": {USER: 1},
        "current_state": {
            "saved_views": [],
            "watchlists": [],
            "reports": [],
            "report_packages": [],
        },
        "current_state_counts": {
            "saved_view_count": 1,
            "active_saved_view_count": 1,
            "watchlist_count": 1,
            "active_watchlist_count": 1,
            "report_count": 1,
            "active_report_count": 1,
            "report_package_count": 0,
        },
        "history_sha256": "i" * 64,
        "filters": {"families": [], "actors": [], "limit": 500},
    }


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = (
        "v27-browser-e2e-stable-secret-key-32chars-minimum"
    )
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import (
        register_dossier_assembly_routes_v21_0,
    )
    from src.socmint import global_investigation_search_routes_v27_0 as global_routes
    from src.socmint import core_record_search_routes_v27_1 as core_routes
    from src.socmint import advanced_search_filters_routes_v27_2 as advanced_routes
    from src.socmint import saved_search_views_routes_v27_3 as saved_routes
    from src.socmint import watchlist_monitoring_routes_v27_4 as watch_routes
    from src.socmint import report_builder_routes_v27_5 as report_routes
    from src.socmint import (
        search_reporting_history_audit_routes_v27_6 as history_routes,
    )

    global_routes.build_global_investigation_search = lambda *a, **k: _global()
    core_routes.build_core_record_search = lambda *a, **k: _core()
    advanced_routes.build_advanced_search_filters = lambda *a, **k: _advanced()
    saved_routes.build_saved_views_workspace = lambda *a, **k: _saved()
    saved_routes.create_view = lambda **k: {
        "status": "saved_view_created",
        "saved_view_id": VIEW_ID,
    }
    saved_routes.revise_view = lambda *a, **k: {
        "status": "saved_view_revised",
        "saved_view_id": VIEW_ID,
    }
    saved_routes.deactivate_view = lambda *a, **k: {"status": "saved_view_deactivated"}
    saved_routes.run_saved_view = lambda *a, **k: {
        "status": "saved_view_executed",
        "saved_view": _view(),
        "execution": _advanced(),
    }
    watch_routes.build_watchlist_workspace = lambda *a, **k: _watchlists()
    watch_routes.create_watchlist = lambda **k: {
        "status": "watchlist_created",
        "watchlist_id": WATCHLIST_ID,
    }
    watch_routes.set_watchlist_status = lambda *a, **k: {
        "status": "watchlist_paused"
        if k.get("status") == "paused"
        else "watchlist_resumed"
    }
    watch_routes.run_watchlist_monitoring = lambda *a, **k: {
        "status": "watchlist_monitoring_completed",
        "monitoring_run_id": "run-e2e",
        "result_count": 1,
    }
    report_routes.current_reports = lambda: [_report()]
    report_routes.latest_packages = lambda: []
    report_routes.create_report_definition = lambda **k: {
        "status": "report_definition_created",
        "report_id": REPORT_ID,
    }
    report_routes.revise_report_definition = lambda *a, **k: {
        "status": "report_definition_revised",
        "report_id": REPORT_ID,
    }
    report_routes.generate_report_package = lambda *a, **k: {
        "status": "report_package_generated",
        "package_id": "package-e2e",
        "files": [],
    }
    history_routes.build_search_reporting_history_audit = lambda *a, **k: _history()

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)

    @app.get("/_v27_e2e_login")
    def _login():
        session["user"] = USER
        session["allowed_case_ids"] = [CASE_ID]
        session["_csrf_token"] = CSRF
        return redirect("/global-search")

    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _post(driver, url: str, payload: dict) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        fetch(arguments[0], {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRF-Token':'v27-e2e-csrf'}, body:JSON.stringify(arguments[1])})
          .then(async r => done({status:r.status, body:await r.json()}))
          .catch(e => done({status:0, body:{error:String(e)}}));
        """,
        url,
        payload,
    )


def run() -> dict:
    report = {
        "schema": "socmint.search_reporting_browser_e2e.v27_7",
        "version": "v27.7.0",
        "checks": [],
    }
    temp = Path(tempfile.mkdtemp(prefix="socmint-v27-e2e-"))
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
        binary = (
            os.getenv("SOCMINT_CHROME_BINARY")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
        )
        executable = os.getenv("SOCMINT_CHROMEDRIVER") or shutil.which("chromedriver")
        if binary:
            options.binary_location = binary
        service = (
            ChromeService(executable_path=executable) if executable else ChromeService()
        )
        driver = webdriver.Chrome(service=service, options=options)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v27_e2e_login")
        pages = [
            ("global_page", "/global-search", "Global Investigation Search"),
            (
                "core_page",
                "/global-search/core-records",
                "Case, Entity, Evidence, and Finding Search",
            ),
            (
                "advanced_page",
                "/global-search/advanced",
                "Advanced Filters and Search Facets",
            ),
            (
                "saved_views_page",
                "/global-search/saved-views",
                "Saved Views and Search Presets",
            ),
            (
                "watchlists_page",
                "/global-search/watchlists",
                "Watchlists and Scheduled Search Monitoring",
            ),
            (
                "reports_page",
                "/global-search/reports",
                "Report Builder and Export Packages",
            ),
            (
                "history_page",
                "/global-search/history",
                "Search, Watchlist, and Reporting History and Audit",
            ),
            (
                "checkpoint_page",
                "/global-search/product-review",
                "Search and Reporting Product Review",
            ),
        ]
        for key, path, phrase in pages:
            driver.get(base + path)
            _check(report, key, phrase.lower() in driver.page_source.lower())

        posts = [
            (
                "saved_view_create",
                "/api/v1/global-search/saved-views",
                {
                    "name": "E2E",
                    "query": "e2e",
                    "filters": {},
                    "visibility": "private",
                    "confirmed": True,
                },
            ),
            (
                "watchlist_create",
                "/api/v1/global-search/watchlists",
                {
                    "name": "E2E",
                    "saved_view_id": VIEW_ID,
                    "cadence": "daily",
                    "notification_rule": "any_change",
                    "confirmed": True,
                },
            ),
            (
                "watchlist_run",
                f"/api/v1/global-search/watchlists/{WATCHLIST_ID}/run",
                {"limit": 25},
            ),
            (
                "report_create",
                "/api/v1/global-search/reports",
                {
                    "name": "E2E",
                    "description": "",
                    "visibility": "private",
                    "sections": [
                        {"section_type": "text", "title": "Notes", "text": "E2E"}
                    ],
                    "export_formats": ["json"],
                    "confirmed": True,
                },
            ),
            (
                "report_generate",
                f"/api/v1/global-search/reports/{REPORT_ID}/generate",
                {"formats": ["json"], "confirmed": True},
            ),
        ]
        for key, path, payload in posts:
            result = _post(driver, base + path, payload)
            _check(
                report,
                key,
                result.get("status") == 200,
                json.dumps(result, sort_keys=True),
            )

        apis = [
            "/api/v1/global-search",
            "/api/v1/global-search/core-records",
            "/api/v1/global-search/advanced",
            "/api/v1/global-search/saved-views",
            "/api/v1/global-search/watchlists",
            "/api/v1/global-search/reports",
            "/api/v1/global-search/history",
            "/api/v1/global-search/product-review-checkpoint",
        ]
        for path in apis:
            driver.get(base + path)
            _check(
                report,
                "api_" + path.rsplit("/", 1)[-1],
                "schema" in driver.page_source or "ready" in driver.page_source,
            )
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
    report["v27_closed"] = report["status"] == "passed"
    report["next_action"] = (
        "begin_v28" if report["v27_closed"] else "resolve_v27_browser_e2e_failures"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
