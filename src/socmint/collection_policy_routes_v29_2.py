from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collection_policy_v29_2 import create_collection_policy, evaluate_collection_job_policy, revise_collection_policy
from .collection_policy_workspace_v29_2 import build_collection_policy_workspace
from .connector_adapter_routes_v29_3 import register_connector_adapter_routes_v29_3
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


def register_collection_policy_routes_v29_2(app):
    @app.get("/collection-operations/policies")
    def collection_policy_workspace_get_v29_2():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("collection_policy_v29_2.html", title="Authorization, Scope, and Collection Policy", payload={"status":"forbidden","error":"administrator required","policies":[],"evaluations":[],"policy_findings":[],"collection_policy_history":[]}), 403
        try:
            review_due_within_days = int(request.args.get("review_due_within_days", "30"))
        except ValueError:
            review_due_within_days = 30
        return render_template("collection_policy_v29_2.html", title="Authorization, Scope, and Collection Policy", payload=build_collection_policy_workspace(review_due_within_days=review_due_within_days))

    @app.get("/api/v1/collection-operations/policies")
    def api_collection_policy_workspace_get_v29_2():
        actor, error = _authorized()
        if error: return error
        try:
            review_due_within_days = int(request.args.get("review_due_within_days", "30"))
        except ValueError:
            review_due_within_days = 30
        return jsonify(build_collection_policy_workspace(review_due_within_days=review_due_within_days))

    @app.post("/api/v1/collection-operations/policies")
    def api_collection_policy_create_post_v29_2():
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = create_collection_policy(actor=actor, name=str(payload.get("name") or ""), description=str(payload.get("description") or ""), permitted_source_classes=payload.get("permitted_source_classes"), permitted_purposes=payload.get("permitted_purposes"), jurisdictions=payload.get("jurisdictions"), case_ids=payload.get("case_ids"), entity_ids=payload.get("entity_ids"), source_ids=payload.get("source_ids"), deny_rules=payload.get("deny_rules"), exclusions=payload.get("exclusions"), valid_from=str(payload.get("valid_from") or ""), expires_at=str(payload.get("expires_at") or ""), review_at=str(payload.get("review_at") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_policy_created")

    @app.post("/api/v1/collection-operations/policies/<policy_id>/revise")
    def api_collection_policy_revise_post_v29_2(policy_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = revise_collection_policy(policy_id, actor=actor, definition=payload.get("definition"), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "collection_policy_revised")

    @app.post("/api/v1/collection-operations/jobs/<collection_job_id>/evaluate-policy")
    def api_collection_policy_evaluate_post_v29_2(collection_job_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = evaluate_collection_job_policy(actor=actor, collection_job_id=collection_job_id, jurisdiction=str(payload.get("jurisdiction") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        if result.get("status") == "collection_policy_evaluated":
            evaluation = result.get("evaluation") or {}
            result["authorization_binding"] = {"collection_job_id":collection_job_id,"policy_evaluation_id":result.get("policy_evaluation_id"),"policy_event_sha256":result.get("policy_event_sha256"),"decision":evaluation.get("decision"),"allowed_by_policy_ids":evaluation.get("allowed_by_policy_ids") or [],"denied_by_policy_ids":evaluation.get("denied_by_policy_ids") or []}
        return jsonify(result), _code(result, "collection_policy_evaluated")

    register_connector_adapter_routes_v29_3(app)
    return app
