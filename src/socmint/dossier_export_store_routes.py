from __future__ import annotations

from flask import jsonify, request, session

from .dossier_export_store import export_store_summary
from .dossier_export_store import load_export_manifest
from .dossier_export_store import persist_export_pack


def _login_required() -> bool:
    return bool(session.get("user"))


def _actor() -> str:
    return str(session.get("user") or "system")


def register_dossier_export_store_routes(app):
    @app.post("/api/v1/dossier-builder/v3/export-store")
    def api_dossier_export_store():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        result = persist_export_pack(
            payload.get("subject") or {},
            evidence=payload.get("evidence") or [],
            analyst_reviewed=bool(payload.get("analyst_reviewed")),
            actor=_actor(),
            audit=True,
        )
        return jsonify(result)

    @app.get("/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/manifest")
    def api_dossier_export_manifest(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(
            load_export_manifest(
                subject_id=subject_id, case_id=case_id, actor=_actor(), audit=True
            )
        )

    @app.get("/api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/summary")
    def api_dossier_export_store_summary(case_id: str, subject_id: str):
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(export_store_summary(subject_id=subject_id, case_id=case_id))

    return app
