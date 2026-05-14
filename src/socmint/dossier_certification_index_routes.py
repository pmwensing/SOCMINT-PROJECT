from __future__ import annotations

from flask import Response, jsonify, session

from .dossier_certification_index import certification_index
from .dossier_certification_index import certification_index_entry
from .dossier_certification_index import certification_index_markdown
from .dossier_certification_index import certification_index_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def _compat_payload(payload):
    if isinstance(payload, dict):
        payload = dict(payload)
        payload["compatibility_alias"] = True
        payload["canonical_route_family"] = "/api/v1/dossier-builder/v3/certification-index/<case_id>"
    return payload


def register_dossier_certification_index_routes(app):
    @app.get("/api/v1/dossier-builder/v3/certification-index/<case_id>")
    def api_dossier_certification_index(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index(case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/certification-index/<case_id>/summary")
    def api_dossier_certification_index_summary(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index_summary(case_id=case_id))

    @app.get("/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown")
    def api_dossier_certification_index_markdown(case_id: str):
        if not _login_required():
            return Response(certification_index_markdown(case_id=case_id), mimetype="text/markdown")

    @app.get("/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>")
    def api_dossier_certification_index_entry(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(certification_index_entry(case_id=case_id, subject_id=subject_id))

    @app.get("/api/v1/dossier-builder/v3/export-certification-index/<case_id>")
    def api_dossier_export_certification_index_compat(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_compat_payload(certification_index(case_id=case_id)))

    @app.get("/api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary")
    def api_dossier_export_certification_index_summary_compat(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_compat_payload(certification_index_summary(case_id=case_id)))

    @app.get("/api/v1/dossier-builder/v3/export-certification-index/<case_id>/review")
    def api_dossier_export_certification_index_review_compat(case_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        index = certification_index(case_id=case_id)
        return jsonify(
            _compat_payload(
                {
                    "schema": index.get("schema"),
                    "status": "clear" if index.get("hold_count", 0) == 0 else "needs_review",
                    "case_id": case_id,
                    "review_count": index.get("hold_count", 0),
                    "review_entries": index.get("held", []),
                }
            )
        )

    return app
