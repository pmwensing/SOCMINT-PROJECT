from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .dossier_release_history_v22_6 import build_release_delivery_history


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_release_history_routes_v22_6(app):
    @app.get("/dossier-release/<case_id>/history")
    def dossier_release_history_get_v22_6(case_id: str):
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        return render_template(
            "dossier_release_history_v22_6.html",
            title="Release and Delivery History",
            payload=build_release_delivery_history(case_id),
        )

    @app.get("/api/v1/dossier-release/<case_id>/history")
    def api_dossier_release_history_get_v22_6(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(build_release_delivery_history(case_id))

    return app
