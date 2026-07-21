from __future__ import annotations

from flask import jsonify, request, session

from .import_observation_promotion_v37_4 import (
    current_promotions,
    find_promotion,
    promote_reviewed_record,
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


def register_import_observation_promotion_routes_v37_4(app):
    @app.get("/api/v1/import-observation-promotions")
    def api_import_promotions_get_v37_4():
        _, error = _authorized()
        if error:
            return error
        items = current_promotions()
        return jsonify(
            {
                "schema": "socmint.import_observation_promotion_inventory.v37_4",
                "version": "v37.4.0",
                "promotions": items,
                "count": len(items),
                "bulk_promotion_available": False,
                "automatic_promotion_available": False,
            }
        )

    @app.post("/api/v1/import-records/<staged_record_id>/promote")
    def api_import_record_promote_post_v37_4(staged_record_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = promote_reviewed_record(
            actor=actor,
            staged_record_id=staged_record_id,
            derivation_method=str(payload.get("derivation_method") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") in {
            "reviewed_import_record_promoted",
            "reviewed_import_record_promotion_reused",
        } else 422
        return jsonify(result), code

    @app.get("/api/v1/import-records/<staged_record_id>/promotion")
    def api_import_record_promotion_get_v37_4(staged_record_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_promotion(staged_record_id)
        if item is None:
            return jsonify({"error": "import record promotion not found"}), 404
        return jsonify(item), 200

    return app
