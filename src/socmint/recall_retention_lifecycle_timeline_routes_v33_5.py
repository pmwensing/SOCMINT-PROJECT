from __future__ import annotations

from flask import jsonify, session

from .case_centric_operator_workspace_routes_v33_6 import (
    register_case_centric_operator_workspace_routes_v33_6,
)
from .recall_retention_lifecycle_timeline_v33_5 import (
    build_case_recall_retention_lifecycle_timeline,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_recall_retention_lifecycle_timeline_routes_v33_5(app):
    @app.get(
        "/api/v1/dissemination-governance/cases/"
        "<case_id>/recall-retention-lifecycle-timeline"
    )
    def get_case_recall_retention_lifecycle_timeline_v33_5(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = build_case_recall_retention_lifecycle_timeline(case_id)
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    register_case_centric_operator_workspace_routes_v33_6(app)
    return app
