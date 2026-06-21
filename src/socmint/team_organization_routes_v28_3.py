from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .access_review_routes_v28_4 import register_access_review_routes_v28_4
from .team_organization_events_v28_3 import append_team_event, create_team, revise_team
from .team_organization_workspace_v28_3 import build_team_organization_workspace
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def _code(result: dict, success: str) -> int:
    return 200 if result.get("status") == success else 422


def register_team_organization_routes_v28_3(app):
    @app.get("/administration/teams")
    def team_organization_workspace_get_v28_3():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "team_organization_administration_v28_3.html",
                title="Team and Organizational Structure",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "teams": [],
                    "organization_findings": [],
                    "team_history": [],
                },
            ), 403
        return render_template(
            "team_organization_administration_v28_3.html",
            title="Team and Organizational Structure",
            payload=build_team_organization_workspace(),
        )

    @app.get("/api/v1/administration/teams")
    def api_team_organization_workspace_get_v28_3():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_team_organization_workspace())

    @app.post("/api/v1/administration/teams")
    def api_team_create_post_v28_3():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_team(
            actor=actor,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_created")

    @app.post("/api/v1/administration/teams/<team_id>/revise")
    def api_team_revise_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = revise_team(
            team_id,
            actor=actor,
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_revised")

    @app.post("/api/v1/administration/teams/<team_id>/members/add")
    def api_team_member_add_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = append_team_event(
            team_id,
            actor=actor,
            event_type="team_member_added",
            username=str(payload.get("username") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_updated")

    @app.post("/api/v1/administration/teams/<team_id>/members/remove")
    def api_team_member_remove_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = append_team_event(
            team_id,
            actor=actor,
            event_type="team_member_removed",
            username=str(payload.get("username") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_updated")

    @app.post("/api/v1/administration/teams/<team_id>/supervisor")
    def api_team_supervisor_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = append_team_event(
            team_id,
            actor=actor,
            event_type="team_supervisor_assigned",
            supervisor_username=str(payload.get("supervisor_username") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_updated")

    @app.post("/api/v1/administration/teams/<team_id>/scope")
    def api_team_scope_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = append_team_event(
            team_id,
            actor=actor,
            event_type="team_scope_bound",
            organizational_scope=str(payload.get("organizational_scope") or ""),
            ownership_boundaries=payload.get("ownership_boundaries") or [],
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_updated")

    @app.post("/api/v1/administration/teams/<team_id>/workload-group")
    def api_team_workload_post_v28_3(team_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = append_team_event(
            team_id,
            actor=actor,
            event_type="team_workload_group_set",
            workload_group=str(payload.get("workload_group") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "team_updated")

    register_access_review_routes_v28_4(app)
    return app
