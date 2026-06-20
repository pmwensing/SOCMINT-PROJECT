from __future__ import annotations

from flask import jsonify, session

from .dossier_export_certification import export_certification_bundle
from .dossier_export_certification import export_certification_statement
from .dossier_export_certification import export_certification_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_export_certification_routes(app):
    @app.get("/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>")
    def api_dossier_export_certification(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            export_certification_bundle(subject_id=subject_id, case_id=case_id)
        )

    @app.get(
        "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/summary"
    )
    def api_dossier_export_certification_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            export_certification_summary(subject_id=subject_id, case_id=case_id)
        )

    @app.get(
        "/api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/statement"
    )
    def api_dossier_export_certification_statement(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            export_certification_statement(subject_id=subject_id, case_id=case_id)
        )

    return app
