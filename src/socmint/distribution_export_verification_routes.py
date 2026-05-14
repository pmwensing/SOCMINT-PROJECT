from __future__ import annotations

from flask import Response, jsonify, session

from .distribution_export_verification import distribution_export_verification_markdown
from .distribution_export_verification import verify_distribution_export


def _login_required() -> bool:
    return bool(session.get("user"))


def register_distribution_export_verification_routes(app):
    @app.get("/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify")
    def api_verify_distribution_export(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(verify_distribution_export(case_id=case_id, subject_id=subject_id))

    @app.get("/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown")
    def api_verify_distribution_export_markdown(case_id: str, subject_id: str):
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(distribution_export_verification_markdown(case_id=case_id, subject_id=subject_id), mimetype="text/markdown")

    return app
