from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .operator_workflow_action_launcher_v17_2 import launch_operator_workflow_action
from .unified_operator_workflow_dashboard_v17_1 import build_unified_operator_workflow_dashboard


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return request.form.to_dict() if request.form else {}


def register_unified_operator_workflow_dashboard_routes_v17_1(app):
    @app.get("/operator/workflow-dashboard")
    def unified_operator_workflow_dashboard_v17_1():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = request.args.get("case_id", "case-delivery-preview")
        payload = build_unified_operator_workflow_dashboard(
            case_id,
            {},
            routes=list(app.url_map.iter_rules()),
        )
        return render_template(
            "unified_operator_workflow_dashboard.html",
            title="Unified Operator Workflow Dashboard",
            payload=payload,
        )

    @app.get("/api/v1/operator/workflow-dashboard/<case_id>")
    def api_unified_operator_workflow_dashboard_get_v17_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_unified_operator_workflow_dashboard(
                case_id,
                {},
                routes=list(app.url_map.iter_rules()),
            )
        )

    @app.post("/api/v1/operator/workflow-dashboard/<case_id>")
    def api_unified_operator_workflow_dashboard_post_v17_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_unified_operator_workflow_dashboard(
                case_id,
                _request_payload(),
                routes=list(app.url_map.iter_rules()),
            )
        )

    @app.post("/api/v1/operator/workflow-dashboard/<case_id>/actions")
    def api_operator_workflow_action_launcher_post_v17_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = launch_operator_workflow_action(
            case_id,
            _request_payload(),
            routes=list(app.url_map.iter_rules()),
        )
        if result.get("status") == "launched":
            status_code = 200
        elif result.get("status") == "confirmation_required":
            status_code = 409
        else:
            status_code = 422
        return jsonify(result), status_code

    return app
