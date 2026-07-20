from __future__ import annotations

from flask import jsonify, request, session

from .entity_candidate_resolution_v36_3 import (
    assess_entity_candidate,
    current_candidates,
    find_candidate,
    record_entity_candidate_decision,
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


def _code(result: dict, expected: str) -> int:
    return 200 if result.get("status") == expected else 422


def register_entity_candidate_resolution_routes_v36_3(app):
    @app.get("/api/v1/entity-accuracy/entity-candidates")
    def api_entity_candidates_get_v36_3():
        _, error = _authorized()
        if error:
            return error
        candidates = current_candidates()
        return jsonify(
            {
                "schema": "socmint.entity_candidate_inventory.v36_3",
                "version": "v36.3.0",
                "candidates": candidates,
                "count": len(candidates),
                "automatic_merge_allowed": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/entity-candidates")
    def api_entity_candidate_post_v36_3():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_entity_candidate(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            entity_a_id=str(payload.get("entity_a_id") or ""),
            entity_b_id=str(payload.get("entity_b_id") or ""),
            signals=payload.get("signals"),
            limitations=payload.get("limitations"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "entity_candidate_assessed")

    @app.get("/api/v1/entity-accuracy/entity-candidates/<candidate_id>")
    def api_entity_candidate_get_v36_3(candidate_id: str):
        _, error = _authorized()
        if error:
            return error
        candidate = find_candidate(candidate_id)
        if candidate is None:
            return jsonify({"error": "entity candidate not found"}), 404
        return jsonify(candidate), 200

    @app.post(
        "/api/v1/entity-accuracy/entity-candidates/<candidate_id>/decision"
    )
    def api_entity_candidate_decision_post_v36_3(candidate_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = record_entity_candidate_decision(
            actor=actor,
            candidate_id=candidate_id,
            decision=str(payload.get("decision") or ""),
            rationale=str(payload.get("rationale") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(
            result,
            "entity_candidate_decision_recorded",
        )

    return app
