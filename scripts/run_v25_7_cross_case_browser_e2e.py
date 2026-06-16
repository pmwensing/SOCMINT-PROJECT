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
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

CORRELATION_ID = "cross-case-entity-e2e"
LINK_ID = "confirmed-cross-case-link-e2e"
CASES = ["case-alpha", "case-bravo"]


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _candidate() -> dict:
    occurrences = [
        {"case_id": "case-alpha", "record_id": 1, "source_action": "case_entity_observed", "field_path": "entity_id", "actor": "analyst-a", "occurred_at": "2026-06-16T02:00:00+00:00", "provenance_sha256": "a" * 64},
        {"case_id": "case-bravo", "record_id": 2, "source_action": "case_entity_observed", "field_path": "entity_id", "actor": "analyst-b", "occurred_at": "2026-06-16T03:00:00+00:00", "provenance_sha256": "b" * 64},
    ]
    return {"correlation_id": CORRELATION_ID, "category": "entity", "match_value": "entity-42", "display_values": ["entity-42"], "case_ids": CASES, "case_count": 2, "occurrence_count": 2, "occurrences": occurrences, "human_review_required": True, "confirmed_match": False}


def _workspace() -> dict:
    return {"schema": "socmint.cross_case_intelligence_workspace.v25_0", "version": "v25.0.0", "status": "ready", "minimum_case_count": 2, "access_scope": {"mode": "restricted", "allowed_case_ids": CASES, "visible_case_ids": CASES}, "counts": {"visible_cases": 2, "source_records": 2, "entity_correlations": 1, "identifier_correlations": 0, "infrastructure_correlations": 0, "evidence_correlations": 0, "timeline_correlations": 0, "repeated_patterns": 0}, "correlations": {"entities": [_candidate()], "identifiers": [], "infrastructure": [], "evidence": [], "timelines": []}, "repeated_patterns": [], "case_provenance": {}, "links": {"portfolio_operations": "/portfolio-operations", "portfolio_history": "/portfolio-operations/history"}, "human_review_required": True, "correlations_are_candidates": True, "source_records_mutated": False, "correlation_record_created": False, "next_action": "review_cross_case_candidates"}


def _review() -> dict:
    return {"schema": "socmint.cross_case_correlation_review.v25_1", "version": "v25.1.0", "correlation_id": CORRELATION_ID, "decision": "accept", "reason": "E2E accepted correlation.", "reviewer": "e2e-analyst", "candidate_snapshot": _candidate(), "candidate_sha256": "c" * 64, "review_decision_id": "correlation-review-e2e", "review_decision_sha256": "d" * 64, "action_record_id": 10, "recorded_at": "2026-06-16T04:00:00+00:00", "workspace_access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "status": "correlation_review_recorded", "source_occurrences_preserved": True, "source_records_mutated": False}


def _registry() -> dict:
    link = {"confirmed_link_id": LINK_ID, "confirmed_link_sha256": "f" * 64, "category": "entity", "match_value": "entity-42", "display_values": ["entity-42"], "case_ids": CASES, "source_occurrences": _candidate()["occurrences"], "source_occurrence_count": 2, "source_occurrences_sha256": "o" * 64, "accepted_review_decision_id": "correlation-review-e2e", "accepted_review_decision_sha256": "d" * 64, "accepted_review": {"workspace_access_scope": {"mode": "restricted", "allowed_case_ids": CASES}}, "registry_record_id": 11, "registered_by": "e2e-analyst", "registered_at": "2026-06-16T05:00:00+00:00"}
    return {"schema": "socmint.cross_case_confirmed_link_registry.v25_2", "version": "v25.2.0", "status": "ready", "access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "confirmed_links": [link], "confirmed_link_count": 1, "accepted_pending_registration": [], "accepted_pending_count": 0, "review_disposition_counts": {"accept": 1}, "review_histories": {CORRELATION_ID: [_review()]}, "unreviewed_candidates_materialized": False, "rejected_deferred_split_history_retained": True, "source_records_mutated": False, "registry_record_created_by_view": False, "next_action": "review_confirmed_cross_case_links"}


def _graph() -> dict:
    nodes = [{"node_id": "case-alpha-node", "node_type": "case", "value": "case-alpha", "label": "case-alpha", "confirmed_link_ids": [LINK_ID], "review_bindings": [{"decision_id": "correlation-review-e2e", "decision_sha256": "d" * 64}], "access_scopes": [{"mode": "restricted"}], "source_occurrences": [], "provenance": [{"confirmed_link_id": LINK_ID}], "node_sha256": "n" * 64}, {"node_id": "entity-node", "node_type": "entity", "value": "entity-42", "label": "entity-42", "confirmed_link_ids": [LINK_ID], "review_bindings": [{"decision_id": "correlation-review-e2e", "decision_sha256": "d" * 64}], "access_scopes": [{"mode": "restricted"}], "source_occurrences": _candidate()["occurrences"], "provenance": [{"confirmed_link_id": LINK_ID}], "node_sha256": "e" * 64}]
    edges = [{"edge_id": "edge-e2e", "edge_type": "case_confirmed_link", "source": "case-alpha-node", "target": "entity-node", "confirmed_link_id": LINK_ID, "confirmed_link_sha256": "f" * 64, "accepted_review_decision_id": "correlation-review-e2e", "accepted_review_decision_sha256": "d" * 64, "source_occurrences": [_candidate()["occurrences"][0]], "source_occurrences_sha256": "o" * 64, "access_scope": {"mode": "restricted"}, "provenance": {"registry_record_id": 11}, "edge_sha256": "x" * 64}]
    return {"schema": "socmint.cross_case_relationship_graph.v25_3", "version": "v25.3.0", "status": "ready", "access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "graph": {"confirmed_link_ids": [LINK_ID], "nodes": nodes, "edges": edges}, "graph_sha256": "g" * 64, "counts": {"confirmed_links": 1, "nodes": 2, "edges": 1, "nodes_by_type": {"case": 1, "entity": 1}, "edges_by_type": {"case_confirmed_link": 1}}, "node_types": ["case", "entity", "evidence", "identifier", "infrastructure", "temporal"], "source_occurrences_preserved": True, "review_bindings_preserved": True, "access_scope_preserved": True, "provenance_preserved": True, "source_records_mutated": False, "graph_record_created": False, "next_action": "review_cross_case_relationship_graph"}


def _impact() -> dict:
    return {"schema": "socmint.cross_case_link_impact_analysis.v25_4", "version": "v25.4.0", "status": "ready", "access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "impact": {"confirmed_link_id": LINK_ID, "confirmed_link_sha256": "f" * 64, "accepted_review_decision_id": "correlation-review-e2e", "accepted_review_decision_sha256": "d" * 64, "affected_case_ids": CASES, "affected_entities": [_graph()["graph"]["nodes"][1]], "evidence_packages": [], "review_queues": [], "closure_states": [], "archive_records": [], "graph_node_ids": ["case-alpha-node", "entity-node"], "graph_edge_ids": ["edge-e2e"]}, "impact_sha256": "i" * 64, "counts": {"affected_cases": 2, "affected_entities": 1, "entities_by_type": {"entity": 1}, "evidence_packages": 0, "review_queue_entries": 0, "closure_states": 0, "archive_records": 0, "graph_nodes": 2, "graph_edges": 1}, "confirmed_link_binding": {"confirmed_link_id": LINK_ID}, "graph_binding": {"graph_sha256": "g" * 64}, "confirmed_link_mutated": False, "graph_mutated": False, "source_records_mutated": False, "impact_record_created": False, "next_action": "review_cross_case_link_impact"}


def _history() -> dict:
    return {"schema": "socmint.cross_case_intelligence_history_audit.v25_5", "version": "v25.5.0", "status": "ready", "generated_at": "2026-06-16T06:00:00+00:00", "access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "history": [{"history_event_id": "audit-10", "event_type": "analyst_decision", "occurred_at": "2026-06-16T04:00:00+00:00", "actor": "e2e-analyst", "correlation_id": CORRELATION_ID, "confirmed_link_id": None, "case_ids": CASES, "source_action": "cross_case_correlation_candidate_review", "source_record_id": 10, "source_binding_sha256": "a" * 64}], "event_count": 1, "event_type_counts": {"analyst_decision": 1}, "actor_counts": {"e2e-analyst": 1}, "correlation_count": 1, "confirmed_link_count": 1, "case_count": 2, "source_bound_event_count": 1, "current_cross_case_intelligence_state": {"confirmed_links": {"count": 1}}, "current_cross_case_intelligence_state_sha256": "h" * 64, "source_records_mutated": False, "history_record_created": False, "next_action": "review_cross_case_intelligence_history"}


def _metrics() -> dict:
    return {"schema": "socmint.cross_case_intelligence_metrics.v25_6", "version": "v25.6.0", "status": "ready", "generated_at": "2026-06-16T06:00:00+00:00", "access_scope": {"mode": "restricted", "allowed_case_ids": CASES}, "metrics": {"candidate_volume": {"total": 1}, "review_dispositions": {"total_reviews": 1}, "confirmation_conversion": {"confirmed_links": 1}, "graph_density": {"nodes": 2, "edges": 1}, "cross_case_reach": {"confirmed_case_count": 2}, "source_occurrence_coverage": {"coverage_percent": 100.0}, "impact_breadth": {"analyzed_links": 1}, "analyst_throughput": {"analyst_count": 1, "analysts": [{"analyst": "e2e-analyst", "review_count": 1, "active_review_days": 1, "reviews_per_active_day": 1.0, "disposition_counts": {"accept": 1}}]}, "confidence_indicators": {"score": 85.0, "band": "strong", "components": {"review_coverage_percent": 100.0}, "interpretation": "operational_indicator_not_probability_or_factual_certainty"}}, "metrics_sha256": "m" * 64, "confidence_is_operational_indicator": True, "confidence_is_not_probability": True, "source_records_mutated": False, "metrics_record_created": False, "next_action": "review_cross_case_intelligence_metrics"}


def _app(db: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    os.environ["SOCMINT_DATA_DIR"] = str(db.parent)
    os.environ["SOCMINT_SECRET_KEY"] = "v25-browser-e2e-stable-secret-key-32chars-minimum"
    os.environ["SOCMINT_AUTO_CREATE_DB"] = "true"

    from src.socmint.dashboard import create_app
    from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes
    from src.socmint import cross_case_intelligence_metrics_routes_v25_6 as metric_routes

    routes.build_cross_case_intelligence_workspace = lambda **kwargs: _workspace()
    routes.correlation_review_history = lambda correlation_id: [_review()]
    routes.review_correlation_candidate = lambda correlation_id, **kwargs: _review()
    routes.build_confirmed_link_registry_workspace = lambda **kwargs: _registry()
    routes.register_confirmed_cross_case_link = lambda correlation_id, **kwargs: {**_registry()["confirmed_links"][0], "status": "confirmed_link_registered", "registry_record_id": 11}
    routes.build_cross_case_relationship_graph = lambda **kwargs: _graph()
    routes.build_cross_case_link_impact_analysis = lambda *args, **kwargs: _impact()
    routes.build_cross_case_intelligence_history_audit = lambda **kwargs: _history()
    metric_routes.build_cross_case_intelligence_metrics = lambda **kwargs: _metrics()

    app = create_app()
    app.config.update(TESTING=True)
    register_dossier_assembly_routes_v21_0(app)

    @app.get("/_v25_e2e_login")
    def _v25_e2e_login():
        session["user"] = "e2e-analyst"
        session["allowed_case_ids"] = CASES
        session["_csrf_token"] = "v25-e2e-csrf"
        return redirect("/cross-case-intelligence")

    return app


def _check(report: dict, key: str, ok: bool, detail: str = "") -> None:
    report["checks"].append({"key": key, "ok": bool(ok), "detail": detail})


def _post_json(driver, url: str, payload: dict) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[arguments.length - 1];
        fetch(arguments[0], {
          method: 'POST', credentials: 'same-origin',
          headers: {'Content-Type': 'application/json', 'X-CSRF-Token': 'v25-e2e-csrf'},
          body: JSON.stringify(arguments[1])
        }).then(async response => done({status: response.status, body: await response.json()}))
          .catch(error => done({status: 0, body: {error: String(error)}}));
        """,
        url,
        payload,
    )


def run() -> dict:
    report = {"schema": "socmint.cross_case_browser_e2e.v25_7", "version": "v25.7.0", "status": "running", "checks": []}
    temp = Path(tempfile.mkdtemp(prefix="socmint-v25-e2e-"))
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
        options.add_argument("--window-size=1440,1200")
        chromium = (
            os.environ.get("SOCMINT_CHROME_BINARY")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
            or shutil.which("google-chrome-stable")
        )
        if chromium:
            options.binary_location = chromium
        driver_path = os.environ.get("SOCMINT_CHROMEDRIVER") or shutil.which("chromedriver")
        service = ChromeService(driver_path) if driver_path else None
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 15)
        base = f"http://127.0.0.1:{port}"
        driver.get(base + "/_v25_e2e_login")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-intelligence-workspace]")))
        _check(report, "candidate_discovery", "entity-42" in driver.page_source)
        _check(report, "review_controls", "Record Decision" in driver.page_source)

        review_result = _post_json(
            driver,
            base + f"/api/v1/cross-case-intelligence/{CORRELATION_ID}/review",
            {"category": "entity", "decision": "accept", "reason": "E2E accepted correlation.", "confirmed": True},
        )
        _check(report, "review_decision_post", review_result.get("status") == 200 and review_result.get("body", {}).get("decision") == "accept", json.dumps(review_result, sort_keys=True))

        link_result = _post_json(
            driver,
            base + f"/api/v1/cross-case-intelligence/{CORRELATION_ID}/confirmed-link",
            {"confirmed": True, "note": "E2E confirmed-link registration."},
        )
        _check(report, "confirmed_link_post", link_result.get("status") == 200 and link_result.get("body", {}).get("confirmed_link_id") == LINK_ID, json.dumps(link_result, sort_keys=True))

        driver.get(base + "/cross-case-intelligence/confirmed-links")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-confirmed-link-registry]")))
        _check(report, "confirmed_link_registry", LINK_ID in driver.page_source)

        driver.get(base + "/cross-case-intelligence/graph")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-relationship-graph]")))
        _check(report, "graph_projection", "entity-42" in driver.page_source)
        _check(report, "graph_renderer", driver.find_elements(By.CSS_SELECTOR, "#cross-case-relationship-graph-canvas svg") != [])

        driver.get(base + f"/cross-case-intelligence/confirmed-links/{LINK_ID}/impact")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-link-impact-analysis]")))
        _check(report, "impact_analysis", "Affected Cases" in driver.page_source)

        driver.get(base + "/cross-case-intelligence/history")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-intelligence-history-audit]")))
        _check(report, "history_audit", "Ordered Cross-Case Intelligence History" in driver.page_source)

        driver.get(base + "/cross-case-intelligence/metrics")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-intelligence-metrics]")))
        _check(report, "metrics_confidence", "Confidence Summary" in driver.page_source)
        _check(report, "confidence_boundary", "not a probability" in driver.page_source)

        driver.get(base + "/cross-case-intelligence/product-review")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cross-case-intelligence-product-review]")))
        _check(report, "product_checkpoint", "ready_for_browser_e2e" in driver.page_source)

        for path, key in (
            ("/api/v1/cross-case-intelligence", "candidate_api"),
            ("/api/v1/cross-case-intelligence/confirmed-links", "registry_api"),
            ("/api/v1/cross-case-intelligence/graph", "graph_api"),
            (f"/api/v1/cross-case-intelligence/confirmed-links/{LINK_ID}/impact", "impact_api"),
            ("/api/v1/cross-case-intelligence/history", "history_api"),
            ("/api/v1/cross-case-intelligence/metrics", "metrics_api"),
            ("/api/v1/cross-case-intelligence/product-review-checkpoint", "checkpoint_api"),
        ):
            driver.get(base + path)
            body = driver.find_element(By.TAG_NAME, "body").text
            _check(report, key, '"status"' in body or '"ready"' in body)
    except Exception as exc:
        _check(report, "browser_exception", False, repr(exc))
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        shutil.rmtree(temp, ignore_errors=True)

    failed = [item for item in report["checks"] if not item["ok"]]
    report["passed_count"] = len(report["checks"]) - len(failed)
    report["failed_count"] = len(failed)
    report["status"] = "passed" if not failed else "failed"
    report["v25_closed"] = not failed
    report["next_action"] = "begin_v26" if not failed else "resolve_v25_browser_e2e_failures"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run()
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
