from __future__ import annotations

from flask import jsonify, send_file, session

from .dossier_export_index import export_index
from .dossier_export_index import find_export_entry
from .dossier_export_index import resolve_export_download_path


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "system")


def register_dossier_export_index_routes(app):
    @app.get("/api/v1/dossier-builder/v3/export-index")
    def api_dossier_export_index():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_index())

    @app.get("/api/v1/dossier-builder/v3/export-index/<case_id>/<subject_id>")
    def api_dossier_export_index_entry(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(find_export_entry(case_id=case_id, subject_id=subject_id))

    @app.get("/api/v1/dossier-builder/v3/export-download/<case_id>/<subject_id>/<filename>")
    def api_dossier_export_download(case_id: str, subject_id: str, filename: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        resolved = resolve_export_download_path(
            case_id=case_id,
            subject_id=subject_id,
            filename=filename,
            actor=_actor(),
            audit=True,
        )
        if resolved["status"] != "ready":
            return jsonify(resolved), 404 if resolved["status"] == "missing" else 400
        return send_file(resolved["path"], as_attachment=True, download_name=resolved["filename"])

    return app
