from __future__ import annotations

from flask import Response, jsonify, request, session

from .entity_profile_intelligence import build_entity_profile_intelligence
from .entity_profile_intelligence import entity_profile_intelligence_markdown
from .entity_profile_intelligence import entity_profile_intelligence_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def _build_from_request() -> dict:
    payload = request.get_json(silent=True) or {}
    return build_entity_profile_intelligence(
        payload.get("subject") or {},
        evidence=payload.get("evidence") or [],
        analyst_reviewed=bool(payload.get("analyst_reviewed")),
        analyst_notes=payload.get("analyst_notes") or [],
    )


def register_entity_profile_intelligence_routes(app):
    @app.post("/api/v1/dossier-builder/v3/intelligence/build")
    def api_entity_profile_intelligence_build():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(_build_from_request())

    @app.post("/api/v1/dossier-builder/v3/intelligence/summary")
    def api_entity_profile_intelligence_summary():
        if not _login_required():
            return jsonify({"error": "login required"}), 401
        return jsonify(entity_profile_intelligence_summary(_build_from_request()))

    @app.post("/api/v1/dossier-builder/v3/intelligence/markdown")
    def api_entity_profile_intelligence_markdown():
        if not _login_required():
            return Response("login required\n", status=401, mimetype="text/plain")
        return Response(entity_profile_intelligence_markdown(_build_from_request()), mimetype="text/markdown")

    return app
