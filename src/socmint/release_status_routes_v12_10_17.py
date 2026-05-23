from __future__ import annotations

from flask import jsonify, session

from .release_status_v12_10_17 import latest_gate_reports, release_status


def _login_required() -> bool:
    return bool(session.get("user"))


def register_release_status_routes(app):
    @app.get("/api/v1/release/status")
    def api_release_status_v12_10_17():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(release_status())

    @app.get("/api/v1/release/gates/latest")
    def api_release_gates_latest_v12_10_17():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(latest_gate_reports())

    return app
