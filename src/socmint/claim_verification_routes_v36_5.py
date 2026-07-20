from __future__ import annotations

from flask import jsonify, request, session

from .claim_verification_v36_5 import (
    assess_claim_verification,
    current_verifications,
    find_verification,
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


def register_claim_verification_routes_v36_5(app):
    @app.get("/api/v1/entity-accuracy/claim-verifications")
    def api_claim_verifications_get_v36_5():
        _, error = _authorized()
        if error:
            return error
        items = current_verifications()
        return jsonify(
            {
                "schema": "socmint.claim_verification_inventory.v36_5",
                "version": "v36.5.0",
                "verifications": items,
                "count": len(items),
                "truth_assigned": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/claims/<claim_id>/verification")
    def api_claim_verification_post_v36_5(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_claim_verification(
            actor=actor,
            claim_id=claim_id,
            source_ids=payload.get("source_ids"),
            identity_context=payload.get("identity_context"),
            temporal_relevance_score=payload.get("temporal_relevance_score"),
            temporal_reason=str(payload.get("temporal_reason") or ""),
            limitations=payload.get("limitations"),
            methodology=str(payload.get("methodology") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "claim_verification_assessed" else 422
        return jsonify(result), code

    @app.get("/api/v1/entity-accuracy/claims/<claim_id>/verification")
    def api_claim_verification_get_v36_5(claim_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_verification(claim_id)
        if item is None:
            return jsonify({"error": "claim verification not found"}), 404
        return jsonify(item), 200

    return app
