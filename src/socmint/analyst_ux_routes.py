from __future__ import annotations

from flask import jsonify, render_template, session

from .analyst_ux import analyst_launchpad
from .analyst_ux import compact_launchpad


def _login_required():
    return bool(session.get("user"))


def register_analyst_ux_routes(app):
    @app.get("/analyst/launchpad")
    def analyst_launchpad_page():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = analyst_launchpad(session["user"])
        try:
            return render_template("analyst_launchpad.html", payload=payload)
        except Exception:
            return jsonify(payload)

    @app.get("/api/v1/analyst/launchpad")
    def api_analyst_launchpad():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(analyst_launchpad(session["user"]))

    @app.get("/api/v1/analyst/launchpad/compact")
    def api_analyst_launchpad_compact():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(compact_launchpad(session["user"]))

    return app
