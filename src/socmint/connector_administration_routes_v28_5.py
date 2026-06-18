from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .connector_administration_events_v28_5 import register_connector, revise_connector, set_connector_enabled, update_auth_readiness
from .connector_administration_workspace_v28_5 import build_connector_administration_workspace
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


def register_connector_administration_routes_v28_5(app):
    @app.get("/administration/connectors")
    def connector_administration_workspace_get_v28_5():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("connector_administration_v28_5.html", title="Connector and Integration Administration", payload={"status":"forbidden","error":"administrator required","connector_summaries":[],"administration_findings":[],"connector_history":[]}), 403
        return render_template("connector_administration_v28_5.html", title="Connector and Integration Administration", payload=build_connector_administration_workspace())

    @app.get("/api/v1/administration/connectors")
    def api_connector_administration_workspace_get_v28_5():
        actor, error = _authorized()
        if error: return error
        return jsonify(build_connector_administration_workspace())

    @app.post("/api/v1/administration/connectors")
    def api_connector_register_post_v28_5():
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = register_connector(actor=actor, name=str(payload.get("name") or ""), connector_type=str(payload.get("connector_type") or ""), authorization_scopes=payload.get("authorization_scopes"), rate_limit_policy=payload.get("rate_limit_policy"), description=str(payload.get("description") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "connector_registered")

    @app.post("/api/v1/administration/connectors/<connector_id>/revise")
    def api_connector_revise_post_v28_5(connector_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = revise_connector(connector_id, actor=actor, name=str(payload.get("name") or ""), connector_type=str(payload.get("connector_type") or ""), authorization_scopes=payload.get("authorization_scopes"), rate_limit_policy=payload.get("rate_limit_policy"), description=str(payload.get("description") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "connector_revised")

    @app.post("/api/v1/administration/connectors/<connector_id>/enable")
    def api_connector_enable_post_v28_5(connector_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = set_connector_enabled(connector_id, actor=actor, enabled=True, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "connector_state_updated")

    @app.post("/api/v1/administration/connectors/<connector_id>/disable")
    def api_connector_disable_post_v28_5(connector_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = set_connector_enabled(connector_id, actor=actor, enabled=False, reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "connector_state_updated")

    @app.post("/api/v1/administration/connectors/<connector_id>/auth-readiness")
    def api_connector_auth_readiness_post_v28_5(connector_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = update_auth_readiness(connector_id, actor=actor, auth_readiness=str(payload.get("auth_readiness") or ""), auth_expires_at=str(payload.get("auth_expires_at") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "connector_auth_readiness_updated")

    return app
