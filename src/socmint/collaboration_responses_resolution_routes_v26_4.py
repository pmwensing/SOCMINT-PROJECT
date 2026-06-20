from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collaboration_responses_resolution_v26_4 import (
    build_collaboration_response_workspace,
    record_collaboration_response,
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


def register_collaboration_responses_resolution_routes_v26_4(app):
    @app.get("/cases/<case_id>/collaboration-responses")
    def collaboration_responses_workspace_get_v26_4(case_id: str):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return render_template(
            "collaboration_responses_resolution_v26_4.html",
            title="Acknowledgements, Responses, and Resolution",
            payload=build_collaboration_response_workspace(case_id),
        )

    @app.get("/api/v1/cases/<case_id>/collaboration-responses")
    def api_collaboration_responses_workspace_get_v26_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return jsonify(build_collaboration_response_workspace(case_id))

    @app.post("/api/v1/cases/<case_id>/collaboration-responses")
    def api_collaboration_response_post_v26_4(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        payload = request.get_json(silent=True) or {}
        result = record_collaboration_response(
            case_id,
            target_type=str(payload.get("target_type") or ""),
            target_id=str(payload.get("target_id") or ""),
            response_type=str(payload.get("response_type") or ""),
            responding_user=str(session.get("user") or "unknown"),
            reason=str(payload.get("reason") or ""),
            unresolved_reason=payload.get("unresolved_reason"),
            resolution_code=payload.get("resolution_code"),
            confirmed=payload.get("confirmed") is True,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get(
            "status"
        ) == "collaboration_response_recorded" else 422

    return app
