from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collaboration_note_events_v26_2 import acknowledge_note, correct_note, create_note, mark_note_read
from .collaboration_notes_workspace_v26_2 import build_collaboration_notes_workspace, find_note


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


def register_collaboration_notes_routes_v26_2(app):
    @app.get("/cases/<case_id>/collaboration-notes")
    def collaboration_notes_workspace_get_v26_2(case_id: str):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return render_template(
            "collaboration_notes_mentions_v26_2.html",
            title="Collaboration Notes and Mentions",
            payload=build_collaboration_notes_workspace(case_id, user_identity=str(session.get("user"))),
        )

    @app.get("/api/v1/cases/<case_id>/collaboration-notes")
    def api_collaboration_notes_workspace_get_v26_2(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        return jsonify(build_collaboration_notes_workspace(case_id, user_identity=str(session.get("user"))))

    @app.post("/api/v1/cases/<case_id>/collaboration-notes")
    def api_collaboration_note_post_v26_2(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        payload = request.get_json(silent=True) or {}
        result = create_note(
            case_id,
            author=str(session.get("user")),
            body=str(payload.get("body") or ""),
            target_type=str(payload.get("target_type") or ""),
            target_id=payload.get("target_id"),
            mentioned_users=payload.get("mentioned_users") if isinstance(payload.get("mentioned_users"), list) else [],
            visibility=str(payload.get("visibility") or "case_team"),
            priority=str(payload.get("priority") or "normal"),
            acknowledgement_required=payload.get("acknowledgement_required") is True,
            confirmed=payload.get("confirmed") is True,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "collaboration_note_recorded" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-notes/<note_id>/correct")
    def api_collaboration_note_correct_post_v26_2(case_id: str, note_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        payload = request.get_json(silent=True) or {}
        previous = find_note(case_id, note_id)
        if previous is None:
            return jsonify({"error": "collaboration note required"}), 404
        result = correct_note(
            case_id,
            note_id,
            author=str(session.get("user")),
            body=str(payload.get("body") or ""),
            reason=str(payload.get("reason") or ""),
            previous_note=previous,
            mentioned_users=payload.get("mentioned_users") if isinstance(payload.get("mentioned_users"), list) else None,
            confirmed=payload.get("confirmed") is True,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "collaboration_note_correction_recorded" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-notes/<note_id>/acknowledge")
    def api_collaboration_note_ack_post_v26_2(case_id: str, note_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        note = find_note(case_id, note_id)
        if note is None:
            return jsonify({"error": "collaboration note required"}), 404
        payload = request.get_json(silent=True) or {}
        result = acknowledge_note(
            case_id,
            note_id,
            acknowledged_by=str(session.get("user")),
            response=payload.get("response"),
            note=note,
            confirmed=payload.get("confirmed") is True,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "collaboration_note_acknowledged" else 422

    @app.post("/api/v1/cases/<case_id>/collaboration-notes/<note_id>/read")
    def api_collaboration_note_read_post_v26_2(case_id: str, note_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        if not _can_access(case_id):
            return jsonify({"error": "case access required"}), 403
        note = find_note(case_id, note_id)
        if note is None:
            return jsonify({"error": "collaboration note required"}), 404
        result = mark_note_read(
            case_id,
            note_id,
            reader=str(session.get("user")),
            note=note,
            allowed_case_ids=_allowed_case_ids(),
            ip_address=request.remote_addr,
        )
        return jsonify(result), 200 if result.get("status") == "collaboration_note_marked_read" else 422

    return app
