from __future__ import annotations

from flask import jsonify, redirect, render_template, request, session, url_for

from .evidence_ingestion_v29_4 import change_artifact_state, derive_observation, register_artifact
from .evidence_ingestion_workspace_v29_4 import build_evidence_ingestion_workspace
from .recovery_operations_routes_v29_5 import register_recovery_operations_routes_v29_5
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


def register_evidence_ingestion_routes_v29_4(app):
    @app.get("/collection-operations/evidence")
    def evidence_ingestion_workspace_get_v29_4():
        actor = str(session.get("user") or "")
        if not actor:
            return redirect(url_for("dashboard.login"))
        if not actor_is_administrator(actor):
            return render_template("evidence_ingestion_v29_4.html", title="Evidence-Safe Ingestion and Provenance", payload={"status":"forbidden","error":"administrator required","artifacts":[],"derived_observations":[],"ingestion_findings":[],"provenance_history":[]}), 403
        return render_template("evidence_ingestion_v29_4.html", title="Evidence-Safe Ingestion and Provenance", payload=build_evidence_ingestion_workspace())

    @app.get("/api/v1/collection-operations/evidence")
    def api_evidence_ingestion_workspace_get_v29_4():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(build_evidence_ingestion_workspace())

    @app.post("/api/v1/collection-operations/evidence")
    def api_evidence_artifact_register_post_v29_4():
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = register_artifact(actor=actor, collection_job_id=str(payload.get("collection_job_id") or ""), attempt_number=payload.get("attempt_number"), source_reference=str(payload.get("source_reference") or ""), acquired_at=str(payload.get("acquired_at") or ""), content_sha256=str(payload.get("content_sha256") or ""), content_type=str(payload.get("content_type") or ""), byte_size=payload.get("byte_size"), acquisition_method=str(payload.get("acquisition_method") or ""), provenance_metadata=payload.get("provenance_metadata"), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "evidence_artifact_registered")

    @app.post("/api/v1/collection-operations/evidence/<artifact_id>/state")
    def api_evidence_artifact_state_post_v29_4(artifact_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = change_artifact_state(actor=actor, artifact_id=artifact_id, to_state=str(payload.get("to_state") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "evidence_artifact_state_changed")

    @app.post("/api/v1/collection-operations/evidence/<artifact_id>/observations")
    def api_evidence_observation_derive_post_v29_4(artifact_id: str):
        actor, error = _authorized()
        if error:
            return error
        payload = _payload()
        result = derive_observation(actor=actor, artifact_id=artifact_id, observation_type=str(payload.get("observation_type") or ""), normalized_value=payload.get("normalized_value"), confidence=str(payload.get("confidence") or ""), derivation_method=str(payload.get("derivation_method") or ""), reason=str(payload.get("reason") or ""), confirmed=payload.get("confirmed") is True, ip_address=request.remote_addr)
        return jsonify(result), _code(result, "evidence_observation_derived")

    register_recovery_operations_routes_v29_5(app)
    return app
