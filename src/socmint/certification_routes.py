from __future__ import annotations

from flask import jsonify, session

from .certification import certification_report
from .certification import certification_summary


def _admin_required() -> bool:
    return bool(session.get("user") and session.get("is_admin"))


def register_certification_routes(app):
    @app.get("/api/v1/admin/certification/report")
    def api_certification_report():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(certification_report())

    @app.get("/api/v1/admin/certification/summary")
    def api_certification_summary():
        if not _admin_required():
            return jsonify({"error": "admin required"}), 403
        return jsonify(certification_summary())

    return app
