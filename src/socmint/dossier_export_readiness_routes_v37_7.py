from __future__ import annotations

from flask import jsonify, request, session

from .dossier_export_readiness_v37_7 import (
    assess_dossier_export_readiness,
    current_export_readiness_records,
    find_export_readiness,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_dossier_export_readiness_routes_v37_7(app):
    @app.get("/api/v1/dossier-export-readiness")
    def api_dossier_export_readiness_get_v37_7():
        _, error = _authorized()
        if error:
            return error
        items = current_export_readiness_records()
        return jsonify(
            {
                "schema": "socmint.dossier_export_readiness_inventory.v37_7",
                "version": "v37.7.0",
                "readiness_records": items,
                "count": len(items),
                "export_created": False,
                "published": False,
            }
        )

    @app.post("/api/v1/dossier-export-readiness")
    def api_dossier_export_readiness_post_v37_7():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_dossier_export_readiness(
            actor=actor,
            snapshot_id=str(payload.get("snapshot_id") or ""),
            redaction_review_id=str(payload.get("redaction_review_id") or ""),
            scope_review_id=str(payload.get("scope_review_id") or ""),
            quality_gate_reference=str(payload.get("quality_gate_reference") or ""),
            approval_reference=str(payload.get("approval_reference") or ""),
            manifest_reference=str(payload.get("manifest_reference") or ""),
            chronology_reviewed=payload.get("chronology_reviewed") is True,
            unresolved_exceptions=payload.get("unresolved_exceptions"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "dossier_export_readiness_recorded" else 422
        return jsonify(result), code

    @app.get("/api/v1/dossier-export-readiness/<readiness_id>")
    def api_dossier_export_readiness_detail_get_v37_7(readiness_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_export_readiness(readiness_id)
        if item is None:
            return jsonify({"error": "dossier export readiness not found"}), 404
        return jsonify(item), 200

    return app
