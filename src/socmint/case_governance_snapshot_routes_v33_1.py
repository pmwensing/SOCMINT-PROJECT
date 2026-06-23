from __future__ import annotations

from flask import jsonify, session

from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .user_account_workspace_v28_1 import actor_is_administrator


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_case_governance_snapshot_routes_v33_1(app):
    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/governance-snapshot"
    )
    def get_case_governance_snapshot_v33_1(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = build_case_governance_snapshot(case_id)
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    return app
