from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .operator_action_session_timeline_v17_5 import (
    SESSION_KEY,
    append_operator_action_history,
    build_operator_action_session_timeline,
)
from .operator_workflow_action_launcher_v17_2 import launch_operator_workflow_action
from .operator_workflow_action_receipt_v17_3 import (
    attach_operator_workflow_action_receipt,
)
from .operator_workflow_action_receipt_verification_v17_4 import (
    verify_operator_workflow_action_receipt,
    verify_operator_workflow_action_receipt_from_request,
)
from .operator_workflow_product_review_checkpoint_v17_7 import (
    build_operator_workflow_product_review_checkpoint,
)
from .unified_operator_workflow_dashboard_v17_1 import (
    build_unified_operator_workflow_dashboard,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return request.form.to_dict() if request.form else {}


def _operator() -> str:
    return str(session.get("user") or "unknown")


def _history() -> list[dict]:
    value = session.get(SESSION_KEY, [])
    return value if isinstance(value, list) else []


def _timeline(case_id: str | None = None) -> dict:
    return build_operator_action_session_timeline(
        _history(),
        case_id=case_id,
        operator=_operator(),
    )


def _dashboard_payload(app, case_id: str, payload: dict) -> dict:
    dashboard = build_unified_operator_workflow_dashboard(
        case_id,
        payload,
        routes=list(app.url_map.iter_rules()),
    )
    dashboard["action_history"] = _timeline(case_id)
    return dashboard


def _append_history(receipt: dict, verification: dict) -> None:
    session[SESSION_KEY] = append_operator_action_history(
        _history(),
        receipt,
        verification,
    )
    session.modified = True


def register_unified_operator_workflow_dashboard_routes_v17_1(app):
    @app.get("/operator/workflow-dashboard")
    def unified_operator_workflow_dashboard_v17_1():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        case_id = request.args.get("case_id", "case-delivery-preview")
        return render_template(
            "unified_operator_workflow_dashboard.html",
            title="Unified Operator Workflow Dashboard",
            payload=_dashboard_payload(app, case_id, {}),
        )

    @app.get("/api/v1/operator/workflow-dashboard/<case_id>")
    def api_unified_operator_workflow_dashboard_get_v17_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_dashboard_payload(app, case_id, {}))

    @app.post("/api/v1/operator/workflow-dashboard/<case_id>")
    def api_unified_operator_workflow_dashboard_post_v17_1(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_dashboard_payload(app, case_id, _request_payload()))

    @app.get("/api/v1/operator/workflow-dashboard/product-review-checkpoint")
    def api_operator_workflow_product_review_checkpoint_get_v17_7():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        result = build_operator_workflow_product_review_checkpoint(
            routes=list(app.url_map.iter_rules())
        )
        return jsonify(result), 200 if result.get("ready") else 409

    @app.get("/api/v1/operator/workflow-dashboard/<case_id>/actions/history")
    def api_operator_action_session_timeline_get_v17_5(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_timeline(case_id))

    @app.post("/api/v1/operator/workflow-dashboard/<case_id>/actions")
    def api_operator_workflow_action_launcher_post_v17_2(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _request_payload()
        operator = _operator()
        result = launch_operator_workflow_action(
            case_id,
            request_payload,
            routes=list(app.url_map.iter_rules()),
        )
        result = attach_operator_workflow_action_receipt(
            case_id,
            result,
            operator=operator,
            recorded_at=(
                str(request_payload.get("recorded_at"))
                if request_payload.get("recorded_at")
                else None
            ),
        )
        result["action_receipt_verification"] = verify_operator_workflow_action_receipt(
            result.get("action_receipt"),
            result,
            expected_operator=operator,
            expected_case_id=case_id,
        )
        _append_history(
            result.get("action_receipt") or {},
            result.get("action_receipt_verification") or {},
        )
        result["action_history"] = _timeline(case_id)
        if result.get("status") == "launched":
            status_code = 200
        elif result.get("status") == "confirmation_required":
            status_code = 409
        else:
            status_code = 422
        return jsonify(result), status_code

    @app.post("/api/v1/operator/workflow-dashboard/<case_id>/actions/verify")
    def api_operator_workflow_action_receipt_verify_post_v17_4(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        request_payload = _request_payload()
        result = verify_operator_workflow_action_receipt_from_request(
            case_id,
            request_payload,
            expected_operator=_operator(),
        )
        receipt = request_payload.get("action_receipt")
        if isinstance(receipt, dict):
            _append_history(receipt, result)
        result["action_history"] = _timeline(case_id)
        return jsonify(result), 200 if result.get("status") == "verified" else 409

    return app
