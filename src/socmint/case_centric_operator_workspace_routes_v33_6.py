from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .case_centric_operator_workspace_v33_6 import (
    build_case_centric_operator_workspace,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _actor():
    return str(session.get("user") or "")


def register_case_centric_operator_workspace_routes_v33_6(app):
    @app.get("/dissemination-governance/cases/<case_id>/workspace")
    def case_centric_operator_workspace_get_v33_6(case_id: str):
        actor = _actor()
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template(
                "case_centric_operator_workspace_v33_6.html",
                title="Case-Centric Dissemination Workspace",
                payload={"status": "forbidden", "error": "administrator required"},
            ), 403
        payload = build_case_centric_operator_workspace(case_id)
        return render_template(
            "case_centric_operator_workspace_v33_6.html",
            title="Case-Centric Dissemination Workspace",
            payload=payload,
        ), 200 if payload.get("status") != "blocked" else 422

    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/operator-workspace"
    )
    def api_case_centric_operator_workspace_get_v33_6(case_id: str):
        actor = _actor()
        if not actor:
            return jsonify({"error": "login required"}), 401
        if not actor_is_administrator(actor):
            return jsonify({"error": "administrator required"}), 403
        payload = build_case_centric_operator_workspace(case_id)
        return jsonify(payload), 200 if payload.get("status") != "blocked" else 422

    return app
