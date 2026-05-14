from __future__ import annotations

from flask import jsonify, session

from .dossier_export_certification_index import certification_index
from .dossier_export_certification_index import certification_index_review_items
from .dossier_export_certification_index import certification_index_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_export_certification_index_routes(app):
    @app.get("/api/v1/dossier-builder/v3/export-certification-index")
    def api_dossier_export_certification_index():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index())

    @app.get("/api/v1/dossier-builder/v3/export-certification-index/summary")
    def api_dossier_export_certification_index_summary():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index_summary())

    @app.get("/api/v1/dossier-builder/v3/export-certification-index/review")
    def api_dossier_export_certification_index_review():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index_review_items())

    return app
