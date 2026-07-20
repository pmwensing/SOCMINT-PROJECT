from __future__ import annotations

from flask import jsonify, request, session

from .relationship_chronology_workflow_v37_6 import build_relationship_chronology
from .user_account_workspace_v28_1 import actor_is_administrator


def register_relationship_chronology_workflow_routes_v37_6(app):
    @app.get("/api/v1/operational-case-intelligence/chronology")
    def api_relationship_chronology_get_v37_6():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(
            build_relationship_chronology(
                case_id=request.args.get("case_id"),
                entity_id=request.args.get("entity_id"),
            )
        ), 200

    return app
