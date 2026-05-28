from __future__ import annotations

from flask import jsonify

from .handoff_status_v13 import build_handoff_status


def register_handoff_status_routes(app) -> None:
    if "api_subject_handoff_status_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_subject_handoff_status_v13(subject_id: int):
        return jsonify(build_handoff_status(subject_id))

    app.add_url_rule(
        "/api/v1/subjects/<int:subject_id>/handoff-status",
        endpoint="api_subject_handoff_status_v13",
        view_func=api_subject_handoff_status_v13,
        methods=["GET"],
    )
