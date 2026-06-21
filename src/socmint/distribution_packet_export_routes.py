from __future__ import annotations

from pathlib import Path

from flask import jsonify, send_file, session

from .distribution_packet_export import build_distribution_packet_export
from .distribution_packet_export import distribution_packet_export_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_distribution_packet_export_routes(app):
    @app.post(
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/build"
    )
    def api_build_distribution_packet_export(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        try:
            return jsonify(
                build_distribution_packet_export(case_id=case_id, subject_id=subject_id)
            ), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>")
    def api_distribution_packet_export_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            distribution_packet_export_summary(case_id=case_id, subject_id=subject_id)
        )

    @app.get(
        "/api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/download"
    )
    def api_download_distribution_packet_export(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        summary = distribution_packet_export_summary(
            case_id=case_id, subject_id=subject_id
        )
        if summary.get("status") == "missing" or not summary.get("zip_path"):
            return jsonify({"error": "distribution export missing"}), 404
        zip_path = Path(str(summary["zip_path"]))
        if not zip_path.exists():
            return jsonify({"error": "distribution export zip missing"}), 404
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"distribution_packet_{case_id}_{subject_id}.zip",
        )

    return app
