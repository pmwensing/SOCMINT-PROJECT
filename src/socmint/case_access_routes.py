from __future__ import annotations

from flask import jsonify, request, session

from .case_access import add_team_member
from .case_access import assign_case
from .case_access import case_access_decision
from .case_access import case_access_summary
from .case_access import team_access_summary
from .case_access import user_case_access


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def _login_required() -> bool:
    return bool(session.get("user"))


def register_case_access_routes(app):
    @app.get("/api/v1/account/case-access")
    def api_account_case_access():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(user_case_access(session["user"]))

    @app.post("/api/v1/cases/<int:case_id>/access/check")
    def api_case_access_check(case_id: int):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        return jsonify(
            case_access_decision(
                session["user"],
                case_id,
                required=payload.get("required", "view"),
            )
        )

    @app.get("/api/v1/admin/case-access/<int:case_id>")
    def api_admin_case_access(case_id: int):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(case_access_summary(case_id))

    @app.post("/api/v1/admin/case-access/<int:case_id>")
    def api_admin_assign_case(case_id: int):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                assign_case(
                    case_id,
                    payload["username"],
                    access_level=payload.get("access_level", "viewer"),
                    actor=session.get("user"),
                    metadata=payload.get("metadata") or {},
                )
            )
        except KeyError as exc:
            return jsonify({"error": f"missing field: {exc}"}), 400

    @app.get("/api/v1/admin/teams/<team_key>/members")
    def api_admin_team_summary(team_key: str):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(team_access_summary(team_key))

    @app.post("/api/v1/admin/teams/<team_key>/members")
    def api_admin_team_member(team_key: str):
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify(
                add_team_member(
                    team_key,
                    payload["username"],
                    role=payload.get("role", "member"),
                    actor=session.get("user"),
                    metadata=payload.get("metadata") or {},
                )
            )
        except KeyError as exc:
            return jsonify({"error": f"missing field: {exc}"}), 400

    return app
