from __future__ import annotations

from flask import jsonify, session

from .production_installer import installer_plan
from .production_installer import installer_readiness_report
from .production_installer import installer_readiness_summary


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_production_installer_routes(app):
    @app.get("/api/v1/admin/installer/plan")
    def api_installer_plan():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(installer_plan())

    @app.get("/api/v1/admin/installer/readiness")
    def api_installer_readiness():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(installer_readiness_report())

    @app.get("/api/v1/admin/installer/readiness/summary")
    def api_installer_readiness_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(installer_readiness_summary())

    return app
