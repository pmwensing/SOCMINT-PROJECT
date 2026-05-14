from __future__ import annotations

from flask import jsonify, request

from .build_audit_report import build_audit_report
from .build_audit_report import build_drift_report


def register_build_audit_routes(app) -> None:
    if "api_v7_5_drift_report" in app.view_functions:
        return

    from .dashboard import admin_required, login_required

    @login_required
    def api_v7_5_drift_report():
        return jsonify(build_drift_report(app))

    @admin_required
    def api_v7_5_audit_report():
        limit = request.args.get("limit", 100, type=int)
        return jsonify(build_audit_report(app, limit=max(1, min(limit, 1000))))

    app.add_url_rule(
        "/api/v1/workbench/drift-report",
        endpoint="api_v7_5_drift_report",
        view_func=api_v7_5_drift_report,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/workbench/audit-report",
        endpoint="api_v7_5_audit_report",
        view_func=api_v7_5_audit_report,
        methods=["GET"],
    )
