from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .public_discovery_capture_workspace_v38_8 import (
    build_public_discovery_capture_workspace,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def register_public_discovery_capture_workspace_routes_v38_8(app):
    @app.get("/public-discovery-capture")
    def public_discovery_capture_workspace_get_v38_8():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "public_discovery_capture_workspace_v38_8.html",
                title="Public Discovery and Capture Workspace",
                payload={
                    "status": "forbidden",
                    "read_only": True,
                    "error": "administrator required",
                    "summary": {},
                    "findings": [],
                    "capability_inventory": [],
                    "gate_decision_inventory": [],
                    "production_enablement_inventory": [],
                    "capture_triage_inventory": [],
                    "uncertain_execution_inventory": [],
                },
            ), 403
        return render_template(
            "public_discovery_capture_workspace_v38_8.html",
            title="Public Discovery and Capture Workspace",
            payload=build_public_discovery_capture_workspace(),
        )

    @app.get("/api/v1/public-discovery-capture/workspace")
    def api_public_discovery_capture_workspace_get_v38_8():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_public_discovery_capture_workspace()), 200

    return app
