from __future__ import annotations

from flask import jsonify, request, session

from .corroboration_claim_v30_1 import change_claim_state, create_corroboration_claim, current_claims
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


def _code(result: dict, expected: str) -> int:
    return 200 if result.get("status") == expected else 422


def register_corroboration_claim_routes_v30_1(app):
    @app.get("/api/v1/analytic-review/claims")
    def api_corroboration_claims_get_v30_1():
        actor, error = _authorized()
        if error:
            return error
        return jsonify({
            "schema": "socmint.corroboration_claims.v30_1",
            "version": "v30.1.0",
            "claims": current_claims(),
        })

    @app.post("/api/v1/analytic-review/claims")
    def api_corroboration_claim_create_post_v30_1():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = create_corroboration_claim(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            entity_id=str(payload.get("entity_id") or ""),
            claim_type=str(payload.get("claim_type") or ""),
            normalized_value=str(payload.get("normalized_value") or ""),
            purpose=str(payload.get("purpose") or ""),
            source_refs=payload.get("source_refs"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "corroboration_claim_created")

    @app.post("/api/v1/analytic-review/claims/<claim_id>/state")
    def api_corroboration_claim_state_post_v30_1(claim_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = change_claim_state(
            actor=actor,
            claim_id=claim_id,
            to_state=str(payload.get("to_state") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "corroboration_claim_state_changed")

    return app
