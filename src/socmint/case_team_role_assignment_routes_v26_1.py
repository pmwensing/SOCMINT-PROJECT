from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .case_team_role_assignment_v26_1 import (
    assign_case_team_role,
    build_case_team_workspace,
    revoke_case_team_role,
)


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _can_access(case_id: str) -> bool:
    allowed = _allowed_case_ids()
    return allowed is None or case_id in allowed


def register_case_team_role_assignment_routes_v26_1(app):
    @app.get("/cases/<case_id>/team")
    def case_team_workspace_get_v26_1(case_id: str):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return render_template(
            "case_team_role_assignment_v26_1.html",
            title="Case Team and Role Assignment",
            payload=build_case_team_workspace(case_id),
        )

    @app.get("/api/v1/cases/<case_id>/team")
    def api_case_team_workspace_get_v26_1(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return jsonify(build_case_team_workspace(case_id))

    @app.post("/api/v1/cases/<case_id>/team/assignments")
    def api_case_team_assignment_post_v26_1(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        payload = request.get_json(silent=True) or {}
        result = assign_case_team_role(
            case_id,
            user_identity=str(payload.get("user_identity") or ""),
            role=str(payload.get("role") or ""),
            assigned_by=str(session.get("user") or "unknown"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            effective_from=payload.get("effective_from"),
            effective_until=payload.get("effective_until"),
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get(
            "status"
        ) == "case_team_assignment_recorded" else 422

    @app.post("/api/v1/cases/<case_id>/team/assignments/<assignment_id>/revoke")
    def api_case_team_revocation_post_v26_1(case_id: str, assignment_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        payload = request.get_json(silent=True) or {}
        result = revoke_case_team_role(
            case_id,
            assignment_id,
            revoked_by=str(session.get("user") or "unknown"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get(
            "status"
        ) == "case_team_revocation_recorded" else 422

    return app
