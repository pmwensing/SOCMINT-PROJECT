from __future__ import annotations

from flask import jsonify, request, session

from .tor_production import hidden_service_status
from .tor_production import production_readiness_report
from .tor_production import torrc_snippet
from .tor_production import upsert_hidden_service_status


def _login_required():
    return bool(session.get("user"))


def _admin_required():
    return bool(session.get("user") and session.get("is_admin"))


def register_tor_routes(app):
    @app.get("/api/v1/tor/status")
    def api_tor_status():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(hidden_service_status())

    @app.get("/api/v1/tor/readiness")
    def api_tor_readiness():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(production_readiness_report())

    @app.get("/api/v1/tor/torrc")
    def api_torrc():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify({"torrc": torrc_snippet()})

    @app.post("/api/v1/admin/tor/status")
    def api_admin_tor_status():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        return jsonify(
            upsert_hidden_service_status(
                service_name=payload.get("service_name", "socmint"),
                enabled=bool(payload.get("enabled", False)),
                onion_hostname=payload.get("onion_hostname"),
                service_dir=payload.get("service_dir", "var/tor/hidden_service"),
                tor_port=int(payload.get("tor_port", 80)),
                target_host=payload.get("target_host", "127.0.0.1"),
                target_port=int(payload.get("target_port", 5000)),
                actor=session.get("user"),
            )
        )

    return app
