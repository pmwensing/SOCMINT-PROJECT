from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .entity_accuracy_workspace_v36_8 import build_entity_accuracy_workspace
from .user_account_workspace_v28_1 import actor_is_administrator


def register_entity_accuracy_workspace_routes_v36_8(app):
    @app.get("/entity-accuracy")
    def entity_accuracy_workspace_get_v36_8():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "entity_accuracy_workspace_v36_8.html",
                title="Entity Accuracy Workspace",
                payload={
                    "status": "forbidden",
                    "read_only": True,
                    "error": "administrator required",
                    "summary": {},
                    "findings": [],
                },
            ), 403
        return render_template(
            "entity_accuracy_workspace_v36_8.html",
            title="Entity Accuracy Workspace",
            payload=build_entity_accuracy_workspace(),
        )

    @app.get("/api/v1/entity-accuracy/workspace")
    def api_entity_accuracy_workspace_get_v36_8():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_entity_accuracy_workspace()), 200

    return app
