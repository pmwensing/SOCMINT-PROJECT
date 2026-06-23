from __future__ import annotations

from flask import jsonify, session

from .action_eligibility_delegate_resolution_v34_1 import (
    build_action_eligibility_delegate_resolution,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def register_action_eligibility_delegate_resolution_routes_v34_1(app):
    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/"
        "action-eligibility"
    )
    def api_action_eligibility_delegate_resolution_get_v34_1(case_id: str):
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_action_eligibility_delegate_resolution(case_id)
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    return app
