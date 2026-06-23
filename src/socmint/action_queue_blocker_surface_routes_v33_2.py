from __future__ import annotations

from flask import jsonify, session

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .user_account_workspace_v28_1 import actor_is_administrator


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_action_queue_blocker_surface_routes_v33_2(app):
    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/action-queue"
    )
    def get_case_action_queue_v33_2(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = build_case_action_queue(case_id)
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/blockers"
    )
    def get_case_blockers_v33_2(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = build_case_action_queue(case_id)
        if payload.get("status") == "blocked":
            return jsonify(payload), 422
        return jsonify(
            {
                "schema": "socmint.case_blocker_surface.v33_2",
                "version": "v33.2.0",
                "case_id": payload.get("case_id"),
                "snapshot_sha256": payload.get("snapshot_sha256"),
                "blockers": payload.get("blockers") or [],
                "action_queue": payload.get("action_queue") or [],
                "read_only": True,
                "actions_executed": False,
            }
        )

    return app
