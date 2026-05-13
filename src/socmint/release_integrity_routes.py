from __future__ import annotations

from flask import jsonify, session

from .release_integrity import release_integrity_report
from .release_integrity import release_integrity_summary
from .release_integrity import route_registration_report


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_release_integrity_routes(app):
    @app.get("/api/v1/admin/release-integrity/report")
    def api_release_integrity_report():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(release_integrity_report(app))

    @app.get("/api/v1/admin/release-integrity/summary")
    def api_release_integrity_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(release_integrity_summary(app))

    @app.get("/api/v1/admin/release-integrity/routes")
    def api_release_integrity_routes():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(route_registration_report(app))

    return app
