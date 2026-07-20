from __future__ import annotations

from flask import jsonify, request, session

from .source_registry_v36_1 import (
    assess_source_reliability,
    current_reliability_profiles,
    current_sources,
    find_source,
    register_source,
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


def register_source_registry_routes_v36_1(app):
    @app.get("/api/v1/entity-accuracy/sources")
    def api_source_records_get_v36_1():
        _, error = _authorized()
        if error:
            return error
        sources = current_sources()
        return jsonify(
            {
                "schema": "socmint.source_registry_inventory.v36_1",
                "version": "v36.1.0",
                "sources": sources,
                "count": len(sources),
                "truth_assigned": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/sources")
    def api_source_record_create_post_v36_1():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = register_source(
            actor=actor,
            case_id=str(payload.get("case_id") or ""),
            source_type=str(payload.get("source_type") or ""),
            publisher_or_operator=str(
                payload.get("publisher_or_operator") or ""
            ),
            canonical_url=str(payload.get("canonical_url") or ""),
            retrieved_url=str(payload.get("retrieved_url") or ""),
            published_at=payload.get("published_at"),
            captured_at=str(payload.get("captured_at") or ""),
            jurisdiction=str(payload.get("jurisdiction") or ""),
            access_method=str(payload.get("access_method") or ""),
            authentication_required=payload.get("authentication_required"),
            authorization_reference=payload.get("authorization_reference"),
            original_or_derived=str(
                payload.get("original_or_derived") or ""
            ),
            terms_and_collection_notes=str(
                payload.get("terms_and_collection_notes") or ""
            ),
            content_sha256=str(payload.get("content_sha256") or ""),
            capture_artifact_id=str(
                payload.get("capture_artifact_id") or ""
            ),
            adapter_name=str(payload.get("adapter_name") or ""),
            adapter_version=str(payload.get("adapter_version") or ""),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "source_record_registered")

    @app.get("/api/v1/entity-accuracy/sources/<source_id>")
    def api_source_record_get_v36_1(source_id: str):
        _, error = _authorized()
        if error:
            return error
        source = find_source(source_id)
        if source is None:
            return jsonify({"error": "source record not found"}), 404
        return jsonify(source), 200

    @app.get(
        "/api/v1/entity-accuracy/sources/<source_id>/reliability-assessments"
    )
    def api_source_reliability_get_v36_1(source_id: str):
        _, error = _authorized()
        if error:
            return error
        if find_source(source_id) is None:
            return jsonify({"error": "source record not found"}), 404
        profiles = current_reliability_profiles(source_id)
        return jsonify(
            {
                "schema": "socmint.source_reliability_inventory.v36_1",
                "version": "v36.1.0",
                "source_id": source_id,
                "profiles": profiles,
                "count": len(profiles),
                "truth_assigned": False,
            }
        )

    @app.post(
        "/api/v1/entity-accuracy/sources/<source_id>/reliability-assessments"
    )
    def api_source_reliability_post_v36_1(source_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_source_reliability(
            actor=actor,
            source_id=source_id,
            claim_type=str(payload.get("claim_type") or ""),
            reliability_band=str(payload.get("reliability_band") or ""),
            components=payload.get("components"),
            reasons=payload.get("reasons"),
            limitations=payload.get("limitations"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        return jsonify(result), _code(result, "source_reliability_assessed")

    return app
