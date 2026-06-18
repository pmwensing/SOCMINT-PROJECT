from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .administration_workspace_v28_0 import build_administration_workspace
from .integration_admin_routes_v28_5 import register_integration_admin_routes_v28_5
from .user_account_routes_v28_1 import register_user_account_routes_v28_1


def register_administration_workspace_routes_v28_0(app):
    @app.get("/administration")
    def administration_workspace_get_v28_0():
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "administration_workspace_v28_0.html",
            title="Administration Workspace",
            payload=build_administration_workspace(),
        )

    @app.get("/api/v1/administration")
    def api_administration_workspace_get_v28_0():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_administration_workspace())

    register_user_account_routes_v28_1(app)
    register_integration_admin_routes_v28_5(app)
    return app
