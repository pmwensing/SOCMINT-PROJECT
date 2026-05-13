from __future__ import annotations

from flask import jsonify, session

from .dossier_export_verification import export_verification_report
from .dossier_export_verification import export_verification_summary
from .dossier_export_verification import verify_artifact_hashes


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_export_verification_routes(app):
    @app.get("/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>")
    def api_dossier_export_verify(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_verification_report(subject_id=subject_id, case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/summary")
    def api_dossier_export_verify_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_verification_summary(subject_id=subject_id, case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/hashes")
    def api_dossier_export_verify_hashes(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(verify_artifact_hashes(subject_id=subject_id, case_id=case_id))

    return app
