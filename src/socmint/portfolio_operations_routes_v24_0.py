from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .portfolio_case_stage_overview_v24_1 import build_case_status_stage_overview
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring


def register_portfolio_operations_routes_v24_0(app):
    @app.get("/portfolio-operations")
    def portfolio_operations_dashboard_get_v24_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        payload = build_portfolio_operations_dashboard()
        payload["stage_overview"] = build_case_status_stage_overview()
        payload["workload_monitoring"] = build_workload_assignment_monitoring()
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

    return app
