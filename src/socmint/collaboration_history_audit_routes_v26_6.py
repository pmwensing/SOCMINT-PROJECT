from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .collaboration_history_audit_v26_6 import build_collaboration_history_audit


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def register_collaboration_history_audit_routes_v26_6(app):
    @app.get("/collaboration/history")
    def collaboration_history_get_v26_6():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "collaboration_history_audit_v26_6.html",
            title="Collaboration History and Audit",
            payload=build_collaboration_history_audit(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            ),
        )

    @app.get("/api/v1/collaboration/history")
    def api_collaboration_history_get_v26_6():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_collaboration_history_audit(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            )
        )

    return app
