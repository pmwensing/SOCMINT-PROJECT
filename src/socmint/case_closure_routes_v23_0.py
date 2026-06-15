from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .case_closure_workspace_v23_0 import build_case_closure_workspace


def _login_required() -> bool:
    return bool(session.get("user"))


def register_case_closure_routes_v23_0(app):
    @app.get("/case-closure/<case_id>")
    def case_closure_workspace_get_v23_0(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "case_closure_workspace_v23_0.html",
            title="Case Closure Workspace",
            payload=build_case_closure_workspace(case_id),
        )

    @app.get("/api/v1/case-closure/<case_id>")
    def api_case_closure_workspace_get_v23_0(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = build_case_closure_workspace(case_id)
        return jsonify(payload), 200 if payload.get("closure_eligible") else 422

    return app
