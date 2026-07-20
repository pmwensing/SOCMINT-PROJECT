from __future__ import annotations

from flask import jsonify, request, session

from .relationship_timeline_v36_6 import (
    assess_relationship_timeline,
    current_relationship_assessments,
    find_relationship_assessment,
    timeline_for_entity,
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


def register_relationship_timeline_routes_v36_6(app):
    @app.get("/api/v1/entity-accuracy/relationship-timeline")
    def api_relationship_timeline_get_v36_6():
        _, error = _authorized()
        if error:
            return error
        entity_id = str(request.args.get("entity_id") or "").strip()
        items = (
            timeline_for_entity(entity_id)
            if entity_id
            else current_relationship_assessments()
        )
        return jsonify(
            {
                "schema": "socmint.relationship_timeline_inventory.v36_6",
                "version": "v36.6.0",
                "assessments": items,
                "count": len(items),
                "relationship_asserted_as_truth": False,
            }
        )

    @app.post("/api/v1/entity-accuracy/relationship-timeline")
    def api_relationship_timeline_post_v36_6():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_relationship_timeline(
            actor=actor,
            claim_id=str(payload.get("claim_id") or ""),
            relationship_type=str(payload.get("relationship_type") or ""),
            subject_entity_id=str(payload.get("subject_entity_id") or ""),
            object_entity_id=str(payload.get("object_entity_id") or ""),
            source_ids=payload.get("source_ids"),
            observation_ids=payload.get("observation_ids"),
            event_time=str(payload.get("event_time") or ""),
            report_time=payload.get("report_time"),
            capture_time=str(payload.get("capture_time") or ""),
            valid_from=payload.get("valid_from"),
            valid_to=payload.get("valid_to"),
            inference_class=str(payload.get("inference_class") or ""),
            inference_warning=str(payload.get("inference_warning") or ""),
            limitations=payload.get("limitations"),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == "relationship_timeline_assessed" else 422
        return jsonify(result), code

    @app.get(
        "/api/v1/entity-accuracy/relationship-timeline/<assessment_id>"
    )
    def api_relationship_timeline_detail_get_v36_6(assessment_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_relationship_assessment(assessment_id)
        if item is None:
            return jsonify({"error": "relationship assessment not found"}), 404
        return jsonify(item), 200

    return app
