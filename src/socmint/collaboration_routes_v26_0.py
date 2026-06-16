from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .case_team_role_assignment_routes_v26_1 import (
    register_case_team_role_assignment_routes_v26_1,
)
from .collaboration_notes_routes_v26_2 import (
    register_collaboration_notes_routes_v26_2,
)
from .collaboration_workspace_v26_0 import build_collaboration_workspace


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def register_collaboration_routes_v26_0(app):
    @app.get("/collaboration")
    def collaboration_workspace_get_v26_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "collaboration_workspace_v26_0.html",
            title="Collaboration Workspace",
            payload=build_collaboration_workspace(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            ),
        )

    @app.get("/api/v1/collaboration")
    def api_collaboration_workspace_get_v26_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_collaboration_workspace(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            )
        )

    register_case_team_role_assignment_routes_v26_1(app)
    register_collaboration_notes_routes_v26_2(app)
    return app
