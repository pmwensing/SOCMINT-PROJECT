from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .reviewer_queue_handoff_summary_v19_6 import (
    build_reviewer_queue_handoff_summary,
)


def _login_required() -> bool:
    return bool(session.get("user"))


def _summary() -> dict:
    return build_reviewer_queue_handoff_summary(
        reviewer=request.args.get("reviewer") or None,
        case_id=request.args.get("case_id") or None,
    )


def register_reviewer_queue_handoff_summary_routes_v19_6(app):
    @app.get("/case-intelligence-review/reviewer-handoff-summary")
    def reviewer_queue_handoff_summary_get_v19_6():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "reviewer_queue_handoff_summary_v19_6.html",
            title="Reviewer Queue Completion / Handoff Summary",
            payload=_summary(),
        )

    @app.get("/api/v1/case-intelligence-review/reviewer-handoff-summary")
    def api_reviewer_queue_handoff_summary_get_v19_6():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_summary())

    return app
