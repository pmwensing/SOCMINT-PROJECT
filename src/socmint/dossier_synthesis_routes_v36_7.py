from __future__ import annotations

from flask import jsonify, request, session

from .dossier_synthesis_v36_7 import (
    create_dossier_synthesis_snapshot,
    current_snapshots,
    find_snapshot,
    latest_snapshot,
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


def register_dossier_synthesis_routes_v36_7(app):
    @app.get("/api/v1/entity-accuracy/dossier-snapshots")
    def api_dossier_snapshots_get_v36_7():
        _, error = _authorized()
        if error:
            return error
        items = current_snapshots()
        return jsonify(
            {
                "schema": "socmint.dossier_synthesis_inventory.v36_7",
                "version": "v36.7.0",
                "snapshots": items,
                "count": len(items),
                "export_created": False,
                "published": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/dossier-snapshots")
    def api_dossier_snapshot_post_v36_7():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_dossier_synthesis_snapshot(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            entity_id=str(payload.get("entity_id") or ""),
            display_label=str(payload.get("display_label") or ""),
            purpose=str(payload.get("purpose") or ""),
            limitations=payload.get("limitations"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = (
            200
            if result.get("status") == "dossier_synthesis_snapshot_created"
            else 422
        )
        return jsonify(result), code

    @app.get("/api/v1/entity-accuracy/dossier-snapshots/latest")
    def api_latest_dossier_snapshot_get_v36_7():
        _, error = _authorized()
        if error:
            return error
        case_id = str(request.args.get("case_id") or "").strip()
        entity_id = str(request.args.get("entity_id") or "").strip()
        if not case_id or not entity_id:
            return jsonify({"error": "case_id and entity_id required"}), 400
        item = latest_snapshot(case_id, entity_id)
        if item is None:
            return jsonify({"error": "dossier snapshot not found"}), 404
        return jsonify(item), 200

    @app.get("/api/v1/entity-accuracy/dossier-snapshots/<snapshot_id>")
    def api_dossier_snapshot_get_v36_7(snapshot_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_snapshot(snapshot_id)
        if item is None:
            return jsonify({"error": "dossier snapshot not found"}), 404
        return jsonify(item), 200

    return app
