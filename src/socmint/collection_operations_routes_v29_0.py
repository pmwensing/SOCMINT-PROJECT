from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .collection_job_routes_v29_1 import register_collection_job_routes_v29_1
from .collection_operations_workspace_v29_0 import build_collection_operations_workspace
from .user_account_workspace_v28_1 import actor_is_administrator


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_collection_operations_routes_v29_0(app):
    @app.get("/collection-operations")
    def collection_operations_workspace_get_v29_0():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "collection_operations_v29_0.html",
                title="Collection Operations Workspace",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "collection_inventory": [],
                    "job_inventory": [],
                    "operator_findings": [],
                    "target_bindings": [],
                },
            ), 403
        try:
            stale_after_hours = int(request.args.get("stale_after_hours", "24"))
        except ValueError:
            stale_after_hours = 24
        return render_template(
            "collection_operations_v29_0.html",
            title="Collection Operations Workspace",
            payload=build_collection_operations_workspace(
                stale_after_hours=stale_after_hours
            ),
        )

    @app.get("/api/v1/collection-operations")
    def api_collection_operations_workspace_get_v29_0():
        actor, error = _authorized()
        if error:
            return error
        try:
            stale_after_hours = int(request.args.get("stale_after_hours", "24"))
        except ValueError:
            stale_after_hours = 24
        return jsonify(
            build_collection_operations_workspace(stale_after_hours=stale_after_hours)
        )

    register_collection_job_routes_v29_1(app)
    return app
