from __future__ import annotations

from flask import jsonify, session

from .guided_analyst_workflow_v37_5 import build_guided_analyst_workflow
from .user_account_workspace_v28_1 import actor_is_administrator


def register_guided_analyst_workflow_routes_v37_5(app):
    @app.get("/api/v1/operational-case-intelligence/workflow")
    def api_guided_analyst_workflow_get_v37_5():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_guided_analyst_workflow()), 200

    return app
