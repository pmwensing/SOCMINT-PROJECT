from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .case_closure_history_v23_6 import build_case_closure_history


def register_case_closure_history_routes_v23_6(app):
    @app.get("/case-closure/<case_id>/history")
    def case_closure_history_get_v23_6(case_id: str):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return render_template(
            "case_closure_history_v23_6.html",
            title="Closure and Archive History",
            payload=build_case_closure_history(case_id),
        )

    @app.get("/api/v1/case-closure/<case_id>/history")
    def api_case_closure_history_get_v23_6(case_id: str):
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(build_case_closure_history(case_id))

    return app
