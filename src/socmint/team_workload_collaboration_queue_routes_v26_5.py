from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .team_workload_collaboration_queue_v26_5 import build_team_workload_collaboration_queue


def _allowed_case_ids() -> set[str] | None:
    value = session.get("allowed_case_ids")
    if value is None:
        return None
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def register_team_workload_collaboration_queue_routes_v26_5(app):
    @app.get("/collaboration/my-work")
    def collaboration_my_work_get_v26_5():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "team_workload_collaboration_queue_v26_5.html",
            title="Team Workload and Collaboration Queue",
            payload=build_team_workload_collaboration_queue(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            ),
        )

    @app.get("/api/v1/collaboration/my-work")
    def api_collaboration_my_work_get_v26_5():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(
            build_team_workload_collaboration_queue(
                str(session.get("user")),
                allowed_case_ids=_allowed_case_ids(),
            )
        )

    return app
