from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .publication_review_workspace_v31_0 import build_publication_review_workspace
from .user_account_workspace_v28_1 import actor_is_administrator


def register_publication_review_routes_v31_0(app):
    @app.get("/publication-review")
    def publication_review_workspace_get_v31_0():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "publication_review_v31_0.html",
                title="Publication Review Workspace",
                payload={"status": "forbidden", "error": "administrator required", "blockers": []},
            ), 403
        return render_template(
            "publication_review_v31_0.html",
            title="Publication Review Workspace",
            payload=build_publication_review_workspace(),
        )

    @app.get("/api/v1/publication-review")
    def api_publication_review_workspace_get_v31_0():
        actor = str(session.get("user") or "")
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        return jsonify(build_publication_review_workspace())

    return app
