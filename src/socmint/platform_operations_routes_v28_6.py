from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .platform_operations_events_v28_6 import acknowledge_incident, open_incident, resolve_incident
from .platform_operations_workspace_v28_6 import build_platform_operations_workspace
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


def register_platform_operations_routes_v28_6(app):
    @app.get("/administration/operations")
    def platform_operations_workspace_get_v28_6():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("platform_operations_v28_6.html", title="Platform Health, Jobs, and Operational Audit", payload={"status":"forbidden","error":"administrator required","operational_findings":[],"operational_incidents":[],"operational_history":[]}), 403
        return render_template("platform_operations_v28_6.html", title="Platform Health, Jobs, and Operational Audit", payload=build_platform_operations_workspace())

    @app.get("/api/v1/administration/operations")
    def api_platform_operations_workspace_get_v28_6():
        actor, error = _authorized()
        if error: return error
        try:
            stale_after_hours = int(request.args.get("stale_after_hours", "24"))
        except ValueError:
            stale_after_hours = 24
        return jsonify(build_platform_operations_workspace(stale_after_hours=stale_after_hours))

    @app.post("/api/v1/administration/operations/incidents")
    def api_operational_incident_open_post_v28_6():
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = open_incident(actor=actor, title=str(payload.get("title") or ""), severity=str(payload.get("severity") or ""), component=str(payload.get("component") or ""), description=str(payload.get("description") or ""), source_binding=payload.get("source_binding"), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "operational_incident_opened")

    @app.post("/api/v1/administration/operations/incidents/<incident_id>/acknowledge")
    def api_operational_incident_acknowledge_post_v28_6(incident_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = acknowledge_incident(incident_id, actor=actor, note=str(payload.get("note") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "operational_incident_acknowledged")

    @app.post("/api/v1/administration/operations/incidents/<incident_id>/resolve")
    def api_operational_incident_resolve_post_v28_6(incident_id: str):
        actor, error = _authorized()
        if error: return error
        payload = _payload()
        result = resolve_incident(incident_id, actor=actor, resolution=str(payload.get("resolution") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "operational_incident_resolved")

    return app
