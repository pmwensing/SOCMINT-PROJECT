from __future__ import annotations

from flask import jsonify, redirect, render_template, session, url_for

from .operator_release_console_v14 import operator_release_console_payload


def _login_required() -> bool:
    return bool(session.get("user"))


def register_operator_release_console_routes_v14(app):
    @app.get("/api/v1/operator/release-console")
    def api_operator_release_console_v14():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(operator_release_console_payload())

    @app.get("/release/console")
    @app.get("/operator/release-console")
    def operator_release_console_v14():
        if not _login_required():
            return redirect(url_for("dashboard.login"))
        payload = operator_release_console_payload()
        return render_template(
            "operator_release_console.html",
            title="Operator Release Console",
            payload=payload,
        )

    return app
