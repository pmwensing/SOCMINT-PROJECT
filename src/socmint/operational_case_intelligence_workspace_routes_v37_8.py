from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .operational_case_intelligence_workspace_v37_8 import (
    build_operational_case_intelligence_workspace,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def register_operational_case_intelligence_workspace_routes_v37_8(app):
    @app.get("/operational-case-intelligence")
    def operational_case_intelligence_workspace_get_v37_8():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "operational_case_intelligence_workspace_v37_8.html",
                title="Operational Case Intelligence Workspace",
                payload={
                    "status": "forbidden",
                    "read_only": True,
                    "error": "administrator required",
                    "summary": {},
                    "findings": [],
                    "export_readiness_inventory": [],
                },
            ), 403
        return render_template(
            "operational_case_intelligence_workspace_v37_8.html",
            title="Operational Case Intelligence Workspace",
            payload=build_operational_case_intelligence_workspace(),
        )

    @app.get("/api/v1/operational-case-intelligence/workspace")
    def api_operational_case_intelligence_workspace_get_v37_8():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_operational_case_intelligence_workspace()), 200

    return app
