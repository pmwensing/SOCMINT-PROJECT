from __future__ import annotations

from flask import jsonify, request, session

from .case_import_pilot_v37_3 import (
    assess_pilot_record,
    build_evidence_location_projection,
    current_review_decisions,
    current_scope_assessments,
    find_review_decision,
    find_scope_assessment,
    record_pilot_review_decision,
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


def register_case_import_pilot_routes_v37_3(app):
    @app.get("/api/v1/case-import-pilot/scope-assessments")
    def api_case_import_scope_assessments_get_v37_3():
        _, error = _authorized()
        if error:
            return error
        items = current_scope_assessments()
        return jsonify(
            {
                "schema": "socmint.case_import_scope_inventory.v37_3",
                "version": "v37.3.0",
                "assessments": items,
                "count": len(items),
            }
        )

    @app.post("/api/v1/case-import-pilot/records/<staged_record_id>/assess")
    def api_case_import_scope_assess_post_v37_3(staged_record_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = assess_pilot_record(
            actor=actor,
            staged_record_id=staged_record_id,
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") in {
            "case_import_scope_assessed",
            "case_import_scope_assessment_reused",
        } else 422
        return jsonify(result), code

    @app.get("/api/v1/case-import-pilot/records/<staged_record_id>/assessment")
    def api_case_import_scope_assessment_get_v37_3(staged_record_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_scope_assessment(staged_record_id)
        if item is None:
            return jsonify({"error": "scope assessment not found"}), 404
        return jsonify(item), 200

    @app.get("/api/v1/case-import-pilot/review-decisions")
    def api_case_import_review_decisions_get_v37_3():
        _, error = _authorized()
        if error:
            return error
        items = current_review_decisions()
        return jsonify(
            {
                "schema": "socmint.case_import_review_inventory.v37_3",
                "version": "v37.3.0",
                "decisions": items,
                "count": len(items),
                "automatic_observation_promotion": False,
            }
        )

    @app.post("/api/v1/case-import-pilot/records/<staged_record_id>/review")
    def api_case_import_review_post_v37_3(staged_record_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = record_pilot_review_decision(
            actor=actor,
            staged_record_id=staged_record_id,
            decision=str(payload.get("decision") or ""),
            quarantine_resolution=payload.get("quarantine_resolution"),
            candidate_resolution_reference=payload.get(
                "candidate_resolution_reference"
            ),
            reason=str(payload.get("reason") or ""),
            confirmed=payload.get("confirmed") is True,
            ip_address=request.remote_addr,
        )
        code = 200 if result.get("status") == (
            "case_import_review_decision_recorded"
        ) else 422
        return jsonify(result), code

    @app.get("/api/v1/case-import-pilot/records/<staged_record_id>/review")
    def api_case_import_review_get_v37_3(staged_record_id: str):
        _, error = _authorized()
        if error:
            return error
        item = find_review_decision(staged_record_id)
        if item is None:
            return jsonify({"error": "review decision not found"}), 404
        return jsonify(item), 200

    @app.post("/api/v1/case-import-pilot/evidence-location-projection")
    def api_case_import_location_projection_post_v37_3():
        _, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = build_evidence_location_projection(
            evidence_id=str(payload.get("evidence_id") or ""),
            location_type=str(payload.get("location_type") or ""),
            location_id=str(payload.get("location_id") or ""),
            path_or_file_id=str(payload.get("path_or_file_id") or ""),
            sha256=str(payload.get("sha256") or ""),
            verified=payload.get("verified") is True,
            notes=str(payload.get("notes") or ""),
        )
        code = 200 if result.get("status") == (
            "evidence_location_projection_ready"
        ) else 422
        return jsonify(result), code

    return app
