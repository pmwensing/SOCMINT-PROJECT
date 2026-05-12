from __future__ import annotations

from flask import jsonify, session

from .beta_readiness import beta_onboarding_steps
from .beta_readiness import beta_readiness_report
from .beta_readiness import beta_readiness_summary


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_beta_readiness_routes(app):
    @app.get("/api/v1/beta/onboarding")
    def api_beta_onboarding():
        return jsonify(beta_onboarding_steps())

    @app.get("/api/v1/admin/beta/readiness")
    def api_beta_readiness():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(beta_readiness_report())

    @app.get("/api/v1/admin/beta/readiness/summary")
    def api_beta_readiness_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(beta_readiness_summary())

    return app
