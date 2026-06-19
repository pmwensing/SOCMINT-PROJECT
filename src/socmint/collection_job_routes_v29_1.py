from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collection_job_contract_v29_1 import create_collection_job_contract, transition_collection_job
from .collection_job_workspace_v29_1 import build_collection_job_workspace
from .collection_policy_routes_v29_2 import register_collection_policy_routes_v29_2
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


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def _policy_binding_valid(binding, collection_job_id: str) -> bool:
    return bool(
        isinstance(binding, dict)
        and binding.get("collection_job_id") == collection_job_id
        and binding.get("policy_evaluation_id")
        and binding.get("policy_event_sha256")
        and binding.get("decision") == "allow"
        and not binding.get("denied_by_policy_ids")
    )


def register_collection_job_routes_v29_1(app):
    @app.get("/collection-operations/jobs")
    def collection_job_workspace_get_v29_1():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("collection_job_contract_v29_1.html", title="Collection Job Contract and State Machine", payload={"status":"forbidden","error":"administrator required","contracts":[],"contract_findings":[],"collection_job_history":[]}), 403
        return render_template("collection_job_contract_v29_1.html", title="Collection Job Contract and State Machine", payload=build_collection_job_workspace())

    @app.get("/api/v1/collection-operations/jobs")
    def api_collection_job_workspace_get_v29_1():
        actor, error = _authorized()
        if error: return error
        return jsonify(build_collection_job_workspace())

    @app.post("/api/v1/collection-operations/jobs")
    def api_collection_job_create_post_v29_1():
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = create_collection_job_contract(actor=actor, connector=str(payload.get("connector") or ""), target_value=str(payload.get("target_value") or ""), target_type=str(payload.get("target_type") or ""), case_id=str(payload.get("case_id") or ""), entity_id=str(payload.get("entity_id") or ""), source_id=str(payload.get("source_id") or ""), authorization_binding=payload.get("authorization_binding"), purpose=str(payload.get("purpose") or ""), idempotency_key=str(payload.get("idempotency_key") or ""), legacy_scan_job_id=payload.get("legacy_scan_job_id"), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_job_contract_created")

    @app.post("/api/v1/collection-operations/jobs/<collection_job_id>/transition")
    def api_collection_job_transition_post_v29_1(collection_job_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        to_state = str(payload.get("to_state") or "")
        binding = payload.get("authorization_binding")
        if to_state == "authorized" and not _policy_binding_valid(binding, collection_job_id):
            return jsonify({"status":"blocked","blockers":[{"key":"allowing_collection_policy_evaluation_required"}],"collection_job_id":collection_job_id,"legacy_scan_job_mutated":False,"connector_execution_performed":False,"case_access_scope_changed":False}), 422
        result = transition_collection_job(collection_job_id=collection_job_id, actor=actor, to_state=to_state, authorization_binding=binding, failure_category=str(payload.get("failure_category") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_job_transitioned")

    register_collection_policy_routes_v29_2(app)
    return app
