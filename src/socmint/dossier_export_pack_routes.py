from __future__ import annotations

from flask import jsonify, request, session

from .dossier_export_pack import build_export_pack
from .dossier_export_pack import export_pack_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_export_pack_routes(app):
    @app.post("/api/v1/dossier-builder/v3/export-pack")
    def api_dossier_export_pack():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        pack = build_export_pack(
            payload.get("subject") or {},
            evidence=payload.get("evidence") or [],
            analyst_reviewed=bool(payload.get("analyst_reviewed")),
        )
        return jsonify(pack)

    @app.post("/api/v1/dossier-builder/v3/export-pack/summary")
    def api_dossier_export_pack_summary():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        pack = build_export_pack(
            payload.get("subject") or {},
            evidence=payload.get("evidence") or [],
            analyst_reviewed=bool(payload.get("analyst_reviewed")),
        )
        return jsonify(export_pack_summary(pack))

    return app
