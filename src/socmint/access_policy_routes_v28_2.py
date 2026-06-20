from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .access_policy_workspace_v28_2 import (
    build_access_policy_workspace,
    evaluate_effective_access,
)
from .team_organization_routes_v28_3 import register_team_organization_routes_v28_3
from .user_account_workspace_v28_1 import actor_is_administrator


def _actor() -> str:
    return str(session.get("user") or "")


def _authorized():
    actor = _actor()
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_access_policy_routes_v28_2(app):
    @app.get("/administration/access-policy")
    def access_policy_workspace_get_v28_2():
        actor = _actor()
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "access_policy_administration_v28_2.html",
                title="Role, Permission, and Access Policy Management",
                payload={
                    "status": "forbidden",
                    "error": "administrator required",
                    "roles": [],
                    "access_rules": [],
                    "permission_matrix": [],
                    "least_privilege_findings": [],
                    "access_policy_history": [],
                },
            ), 403
        return render_template(
            "access_policy_administration_v28_2.html",
            title="Role, Permission, and Access Policy Management",
            payload=build_access_policy_workspace(),
        )

    @app.get("/api/v1/administration/access-policy")
    def api_access_policy_workspace_get_v28_2():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_access_policy_workspace())

    @app.get("/api/v1/administration/access-policy/evaluate")
    def api_access_policy_evaluate_get_v28_2():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            evaluate_effective_access(
                str(request.args.get("username") or ""),
                str(request.args.get("case_id") or ""),
            )
        )

    from .access_policy_write_routes_v28_2 import (
        register_access_policy_write_routes_v28_2,
    )

    register_access_policy_write_routes_v28_2(app)
    register_team_organization_routes_v28_3(app)
    return app
