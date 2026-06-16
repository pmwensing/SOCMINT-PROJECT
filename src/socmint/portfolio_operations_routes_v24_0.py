from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .portfolio_blocked_overdue_queue_v24_3 import build_blocked_overdue_case_queue
from .portfolio_case_stage_overview_v24_1 import build_case_status_stage_overview
from .portfolio_operational_metrics_v24_5 import build_operational_metrics
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard
from .portfolio_supervisor_escalation_v24_4 import (
    acknowledge_escalation,
    build_escalation_control_state,
    reassign_escalation,
    record_escalation,
    resolve_escalation,
)
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring


def register_portfolio_operations_routes_v24_0(app):
    @app.get("/portfolio-operations")
    def portfolio_operations_dashboard_get_v24_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_portfolio_operations_dashboard()
        payload["stage_overview"] = build_case_status_stage_overview()
        payload["workload_monitoring"] = build_workload_assignment_monitoring()
        payload["blocked_overdue_queue"] = build_blocked_overdue_case_queue()
        payload["escalation_controls"] = build_escalation_control_state()
        payload["operational_metrics"] = build_operational_metrics()
        return render_template(
            "portfolio_operations_dashboard_v24_0.html",
            title="Portfolio Operations Dashboard",
            payload=payload,
        )

    @app.get("/api/v1/portfolio-operations")
    def api_portfolio_operations_dashboard_get_v24_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = build_portfolio_operations_dashboard()
        payload["stage_overview"] = build_case_status_stage_overview()
        payload["workload_monitoring"] = build_workload_assignment_monitoring()
        payload["blocked_overdue_queue"] = build_blocked_overdue_case_queue()
        payload["escalation_controls"] = build_escalation_control_state()
        payload["operational_metrics"] = build_operational_metrics()
        return jsonify(payload)

    @app.get("/api/v1/portfolio-operations/stage-overview")
    def api_portfolio_stage_overview_get_v24_1():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_status_stage_overview())

    @app.get("/api/v1/portfolio-operations/workload-monitoring")
    def api_portfolio_workload_monitoring_get_v24_2():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_workload_assignment_monitoring())

    @app.get("/api/v1/portfolio-operations/blocked-overdue")
    def api_portfolio_blocked_overdue_get_v24_3():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_blocked_overdue_case_queue())

    @app.get("/api/v1/portfolio-operations/escalations")
    def api_portfolio_escalations_get_v24_4():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_escalation_control_state())

    @app.get("/api/v1/portfolio-operations/metrics")
    def api_portfolio_metrics_get_v24_5():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_operational_metrics())

    def actor() -> str:
        return str(session.get("user") or "unknown")

    @app.post("/api/v1/portfolio-operations/<case_id>/escalate")
    def api_portfolio_escalate_post_v24_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = record_escalation(case_id, confirmed=payload.get("confirmed") is True, supervisor=actor(), reason=str(payload.get("reason") or ""), note=str(payload.get("note") or ""), ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "escalate_recorded" else 422

    @app.post("/api/v1/portfolio-operations/<case_id>/acknowledge")
    def api_portfolio_acknowledge_post_v24_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = acknowledge_escalation(case_id, confirmed=payload.get("confirmed") is True, supervisor=actor(), note=str(payload.get("note") or ""), ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "acknowledge_recorded" else 422

    @app.post("/api/v1/portfolio-operations/<case_id>/reassign")
    def api_portfolio_reassign_post_v24_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = reassign_escalation(case_id, confirmed=payload.get("confirmed") is True, supervisor=actor(), assigned_reviewer=str(payload.get("assigned_reviewer") or ""), note=str(payload.get("note") or ""), ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "reassign_recorded" else 422

    @app.post("/api/v1/portfolio-operations/<case_id>/resolve")
    def api_portfolio_resolve_post_v24_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = resolve_escalation(case_id, confirmed=payload.get("confirmed") is True, supervisor=actor(), resolution=str(payload.get("resolution") or ""), note=str(payload.get("note") or ""), ip_address=request.remote_addr)
        return jsonify(result), 200 if result.get("status") == "resolve_recorded" else 422

    return app
