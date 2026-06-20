from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collection_quality_routes_v29_6 import register_collection_quality_routes_v29_6
from .recovery_operations_v29_5 import create_recovery_plan, decide_retry, record_operator_intervention, request_retry
from .recovery_operations_workspace_v29_5 import build_recovery_operations_workspace
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error":"login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error":"administrator required"}), 403)
    return actor, None


def _code(result: dict, expected: str) -> int:
    return 200 if result.get("status") == expected else 422


def register_recovery_operations_routes_v29_5(app):
    @app.get("/collection-operations/recovery")
    def recovery_operations_workspace_get_v29_5():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("recovery_operations_v29_5.html", title="Retry, Recovery, and Operator Intervention", payload={"status":"forbidden","error":"administrator required","retry_requests":[],"recovery_plans":[],"operator_interventions":[],"recovery_findings":[],"recovery_history":[]}), 403
        return render_template("recovery_operations_v29_5.html", title="Retry, Recovery, and Operator Intervention", payload=build_recovery_operations_workspace())

    @app.get("/api/v1/collection-operations/recovery")
    def api_recovery_operations_workspace_get_v29_5():
        actor, error = _authorized()
        if error: return error
        return jsonify(build_recovery_operations_workspace())

    @app.post("/api/v1/collection-operations/jobs/<collection_job_id>/retry-requests")
    def api_retry_request_post_v29_5(collection_job_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = request_retry(actor=actor, collection_job_id=collection_job_id, idempotency_key=str(payload.get("idempotency_key") or ""), backoff_seconds=payload.get("backoff_seconds"), earliest_retry_at=str(payload.get("earliest_retry_at") or ""), retry_window_ends_at=str(payload.get("retry_window_ends_at") or ""), max_attempts=payload.get("max_attempts"), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_retry_requested")

    @app.post("/api/v1/collection-operations/retry-requests/<retry_request_id>/decision")
    def api_retry_decision_post_v29_5(retry_request_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = decide_retry(actor=actor, retry_request_id=retry_request_id, approved=payload.get("approved") is True, decision_reason=str(payload.get("decision_reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_retry_decided")

    @app.post("/api/v1/collection-operations/jobs/<collection_job_id>/recovery-plans")
    def api_recovery_plan_post_v29_5(collection_job_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = create_recovery_plan(actor=actor, collection_job_id=collection_job_id, retry_request_id=str(payload.get("retry_request_id") or ""), plan_type=str(payload.get("plan_type") or ""), steps=payload.get("steps"), operator_required=payload.get("operator_required") is True, replacement_job_id=str(payload.get("replacement_job_id") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_recovery_plan_created")

    @app.post("/api/v1/collection-operations/jobs/<collection_job_id>/interventions")
    def api_operator_intervention_post_v29_5(collection_job_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = record_operator_intervention(actor=actor, collection_job_id=collection_job_id, intervention_type=str(payload.get("intervention_type") or ""), resolution=str(payload.get("resolution") or ""), replacement_job_id=str(payload.get("replacement_job_id") or ""), apply_terminal_transition=payload.get("apply_terminal_transition") is True, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_operator_intervention_recorded")

    register_collection_quality_routes_v29_6(app)
    return app
