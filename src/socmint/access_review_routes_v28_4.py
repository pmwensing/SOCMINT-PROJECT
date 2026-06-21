from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .access_review_events_v28_4 import (
    assign_review,
    close_review,
    create_review,
    decide_review,
)
from .access_review_workspace_v28_4 import build_access_review_workspace
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


def register_access_review_routes_v28_4(app):
    @app.get("/administration/access-reviews")
    def access_review_workspace_get_v28_4():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "access_review_certification_v28_4.html",
                title="Access Review and Certification",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "reviews": [],
                    "pending_assignments": [],
                    "remediation_queue": [],
                    "access_review_history": [],
                },
            ), 403
        return render_template(
            "access_review_certification_v28_4.html",
            title="Access Review and Certification",
            payload=build_access_review_workspace(),
        )

    @app.get("/api/v1/administration/access-reviews")
    def api_access_review_workspace_get_v28_4():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_access_review_workspace())

    @app.post("/api/v1/administration/access-reviews")
    def api_access_review_create_post_v28_4():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_review(
            actor=actor,
            name=str(payload.get("name") or ""),
            scope=payload.get("scope"),
            due_at=str(payload.get("due_at") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "access_review_created")

    @app.post("/api/v1/administration/access-reviews/<review_id>/assign")
    def api_access_review_assign_post_v28_4(review_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assign_review(
            review_id,
            actor=actor,
            reviewer_username=str(payload.get("reviewer_username") or ""),
            subject_type=str(payload.get("subject_type") or ""),
            subject_id=str(payload.get("subject_id") or ""),
            case_id=str(payload.get("case_id") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "access_review_assigned")

    @app.post("/api/v1/administration/access-reviews/<review_id>/decide")
    def api_access_review_decide_post_v28_4(review_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = decide_review(
            review_id,
            actor=actor,
            assignment_id=str(payload.get("assignment_id") or ""),
            decision=str(payload.get("decision") or ""),
            retained_permissions=payload.get("retained_permissions"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "access_review_decided")

    @app.post("/api/v1/administration/access-reviews/<review_id>/close")
    def api_access_review_close_post_v28_4(review_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = close_review(
            review_id,
            actor=actor,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "access_review_closed")

    return app
