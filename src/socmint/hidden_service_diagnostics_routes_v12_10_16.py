from __future__ import annotations

from flask import jsonify, session

from .tor_production import tor_hidden_service_diagnostics


def register_hidden_service_diagnostics_routes(app):
    @app.get("/api/v1/tor/diagnostics")
    def api_tor_diagnostics_v12_10_16():
        if not session.get("user"):
            return jsonify({"error": "login required"}), 401
        return jsonify(tor_hidden_service_diagnostics())

    return app
