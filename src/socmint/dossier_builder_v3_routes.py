from __future__ import annotations

from flask import jsonify, request, session

from .dossier_builder_v3 import build_dossier_payload
from .dossier_builder_v3 import dossier_builder_capabilities
from .dossier_builder_v3 import dossier_builder_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def register_dossier_builder_v3_routes(app):
    @app.get("/api/v1/dossier-builder/v3/capabilities")
    def api_dossier_builder_v3_capabilities():
        return jsonify(dossier_builder_capabilities())

    @app.post("/api/v1/dossier-builder/v3/build")
    def api_dossier_builder_v3_build():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        dossier = build_dossier_payload(
            payload.get("subject") or {},
            evidence=payload.get("evidence") or [],
            analyst_reviewed=bool(payload.get("analyst_reviewed")),
        )
        return jsonify(dossier)

    @app.post("/api/v1/dossier-builder/v3/summary")
    def api_dossier_builder_v3_summary():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        payload = request.get_json(silent=True) or {}
        dossier = build_dossier_payload(
            payload.get("subject") or {},
            evidence=payload.get("evidence") or [],
            analyst_reviewed=bool(payload.get("analyst_reviewed")),
        )
        return jsonify(dossier_builder_summary(dossier))

    return app
