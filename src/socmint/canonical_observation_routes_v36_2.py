from __future__ import annotations

from flask import jsonify, request, session

from .canonical_observation_v36_2 import (
    change_canonical_observation_state,
    current_observations,
    find_canonical_observation,
    register_canonical_observation,
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


def register_canonical_observation_routes_v36_2(app):
    @app.get("/api/v1/entity-accuracy/observations")
    def api_canonical_observations_get_v36_2():
        _, error = _authorized()
        if error:
            return error
        state_filter = str(request.args.get("state") or "").strip()
        items = current_observations()
        if state_filter:
            items = [
                item
                for item in items
                if item.get("observation_state") == state_filter
            ]
        return jsonify(
            {
                "schema": "socmint.canonical_observation_inventory.v36_2",
                "version": "v36.2.0",
                "observations": items,
                "count": len(items),
                "truth_assigned": False,
                "identity_assigned": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/observations")
    def api_canonical_observation_post_v36_2():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = register_canonical_observation(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            source_id=str(payload.get("source_id") or ""),
            source_observation_id=str(
                payload.get("source_observation_id") or ""
            ),
            tool_run_id=str(payload.get("tool_run_id") or ""),
            artifact_id=str(payload.get("artifact_id") or ""),
            observation_type=str(payload.get("observation_type") or ""),
            raw_value=payload.get("raw_value"),
            normalized_value=payload.get("normalized_value"),
            observed_at=str(payload.get("observed_at") or ""),
            valid_time_start=payload.get("valid_time_start"),
            valid_time_end=payload.get("valid_time_end"),
            extraction_method=str(payload.get("extraction_method") or ""),
            extraction_confidence=payload.get("extraction_confidence"),
            context=payload.get("context"),
            parent_observation_id=payload.get("parent_observation_id"),
            adapter_format=str(payload.get("adapter_format") or ""),
            adapter_name=str(payload.get("adapter_name") or ""),
            adapter_version=str(payload.get("adapter_version") or ""),
            quarantine_reasons=payload.get("quarantine_reasons"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(
            result,
            "canonical_observation_registered",
        )

    @app.get(
        "/api/v1/entity-accuracy/observations/<canonical_observation_id>"
    )
    def api_canonical_observation_get_v36_2(canonical_observation_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_canonical_observation(canonical_observation_id)
        if item is None:
            return jsonify({"error": "canonical observation not found"}), 404
        return jsonify(item), 200

    @app.post(
        "/api/v1/entity-accuracy/observations/"
        "<canonical_observation_id>/state"
    )
    def api_canonical_observation_state_post_v36_2(
        canonical_observation_id: str,
    ):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = change_canonical_observation_state(
            actor=actor,
            canonical_observation_id=canonical_observation_id,
            to_state=str(payload.get("to_state") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(
            result,
            "canonical_observation_state_changed",
        )

    return app
