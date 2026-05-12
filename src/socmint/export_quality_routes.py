from __future__ import annotations

from flask import jsonify, session

from .export_quality import export_quality_report
from .export_quality import export_quality_summary


def _login_required():
    return bool(session.get("user"))


def register_export_quality_routes(app):
    @app.get("/api/v1/spine/subjects/<int:subject_id>/export-quality")
    def api_export_quality(subject_id: int):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_quality_report(subject_id, redacted=True))

    @app.get("/api/v1/spine/subjects/<int:subject_id>/export-quality/summary")
    def api_export_quality_summary(subject_id: int):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_quality_summary(subject_id))

    return app
