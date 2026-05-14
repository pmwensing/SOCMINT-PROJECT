from __future__ import annotations

from flask import Response, jsonify, request, session

from .dossier_evidence_manifest_v7_5 import attach_evidence_appendix
from .dossier_export_enforcement_v7_5 import attach_export_enforcement
from .dossier_export_enforcement_v7_5 import export_block_message
from .entity_profile_intelligence import build_entity_profile_intelligence
from .entity_profile_intelligence import entity_profile_intelligence_markdown
from .entity_profile_intelligence import entity_profile_intelligence_summary


def _login_required() -> bool:
    return bool(session.get("user"))


def _request_payload() -> dict:
    return request.get_json(silent=True) or {}


def _export_mode(payload: dict) -> str:
    return str(payload.get("export_mode") or request.args.get("mode") or "draft")


def _raw_evidence(payload: dict) -> list[dict]:
    evidence = payload.get("evidence") or []
    return evidence if isinstance(evidence, list) else []


def _build_from_payload(payload: dict) -> dict:
    return build_entity_profile_intelligence(
        payload.get("subject") or {},
        evidence=_raw_evidence(payload),
        analyst_reviewed=bool(payload.get("analyst_reviewed")),
        analyst_notes=payload.get("analyst_notes") or [],
    )


def _build_from_request() -> dict:
    payload = _request_payload()
    built = _build_from_payload(payload)
    built = attach_evidence_appendix(built, raw_evidence=_raw_evidence(payload))
    return attach_export_enforcement(built, mode=_export_mode(payload))


def _blocked_response(payload: dict):
    decision = payload.get("export_enforcement") or {}
    if decision.get("allowed") is False:
        return jsonify({"error": export_block_message(decision), "export_enforcement": decision}), 409
    return None


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
        payload = _build_from_request()
        blocked = _blocked_response(payload)
        if blocked:
            return blocked
        return Response(entity_profile_intelligence_markdown(payload), mimetype="text/markdown")

    return app
