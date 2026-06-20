from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .evidence_ingestion_v29_4 import current_artifacts, observations

SCHEMA = "socmint.collection_quality.v29_6"
VERSION = "v29.6.0"
ACTIONS = ("collection_quality_assessed", "dossier_contribution_reviewed")
TRUST_TIERS = ("untrusted", "limited", "supported", "trusted")
CONTRIBUTION_STATES = ("pending_review", "approved", "held", "rejected")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "dossier_mutated": False,
        "evidence_mutated": False,
        "connector_execution_performed": False,
    }


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "audit_target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(actor=actor, action=action, target_value=target, ip_address=ip_address, details=_canonical(event))
        session.add(row)
        session.commit()
        session.refresh(row)
        return {**event, "audit_record_id": row.id, "actor": actor, "source_action": action, "audit_target_value": target, "recorded_at": row.created_at.isoformat() if row.created_at else None}
    finally:
        session.close()


def quality_assessments() -> list[dict[str, Any]]:
    return [item for item in history() if item.get("event_type") == "collection_quality_assessed"]


def contribution_reviews() -> list[dict[str, Any]]:
    return [item for item in history() if item.get("event_type") == "dossier_contribution_reviewed"]


def find_assessment(assessment_id: str) -> dict[str, Any] | None:
    return next((item for item in quality_assessments() if item.get("quality_assessment_id") == assessment_id), None)


def latest_assessment_for_artifact(artifact_id: str) -> dict[str, Any] | None:
    matches = [item for item in quality_assessments() if item.get("artifact_id") == artifact_id]
    return matches[-1] if matches else None


def latest_contribution_review(assessment_id: str) -> dict[str, Any] | None:
    matches = [item for item in contribution_reviews() if item.get("quality_assessment_id") == assessment_id]
    return matches[-1] if matches else None


def _score_artifact(artifact: dict[str, Any]) -> tuple[int, list[dict[str, str]]]:
    score = 0
    findings: list[dict[str, str]] = []
    state = str(artifact.get("artifact_state") or "registered")
    if artifact.get("chain_of_custody_complete") is True:
        score += 25
    else:
        findings.append({"severity": "high", "key": "chain_of_custody_incomplete"})
    if artifact.get("contract_binding_sha256") and artifact.get("acquisition_sha256"):
        score += 20
    else:
        findings.append({"severity": "high", "key": "deterministic_provenance_binding_missing"})
    if state == "accepted":
        score += 25
    elif state == "registered":
        score += 5
        findings.append({"severity": "medium", "key": "artifact_acceptance_pending"})
    else:
        findings.append({"severity": "high", "key": f"artifact_state_{state}"})
    observation_count = int(artifact.get("observation_count") or 0)
    if observation_count:
        score += min(20, 10 + observation_count * 2)
    else:
        findings.append({"severity": "medium", "key": "no_derived_observations"})
    if artifact.get("duplicate_of_artifact_id"):
        findings.append({"severity": "medium", "key": "duplicate_artifact"})
    else:
        score += 10
    return min(score, 100), findings


def assess_collection_quality(*, actor: str, artifact_id: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    artifact = next((item for item in current_artifacts() if item.get("artifact_id") == artifact_id), None)
    reason = str(reason or "").strip()
    if artifact is None:
        return blocked("evidence_artifact_required")
    if confirmed is not True:
        return blocked("explicit_quality_assessment_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")
    score, findings = _score_artifact(artifact)
    if score >= 85:
        trust_tier = "trusted"
    elif score >= 65:
        trust_tier = "supported"
    elif score >= 40:
        trust_tier = "limited"
    else:
        trust_tier = "untrusted"
    observation_ids = [item.get("observation_id") or item.get("artifact_event_id") for item in observations() if item.get("artifact_id") == artifact_id]
    binding = {
        "artifact_id": artifact_id,
        "artifact_event_id": (artifact.get("state_history") or [artifact])[-1].get("artifact_event_id"),
        "artifact_event_sha256": (artifact.get("state_history") or [artifact])[-1].get("artifact_event_sha256"),
        "content_sha256": artifact.get("content_sha256"),
        "observation_ids": observation_ids,
    }
    content = {
        "event_type": "collection_quality_assessed",
        "artifact_id": artifact_id,
        "collection_job_id": artifact.get("collection_job_id"),
        "case_id": (artifact.get("contract_binding") or {}).get("case_id"),
        "entity_id": (artifact.get("contract_binding") or {}).get("entity_id"),
        "artifact_state": artifact.get("artifact_state"),
        "observation_count": len(observation_ids),
        "quality_score": score,
        "trust_tier": trust_tier,
        "quality_findings": findings,
        "artifact_binding": binding,
        "artifact_binding_sha256": _sha(binding),
        "contribution_state": "pending_review",
        "reason": reason,
    }
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "quality_assessment_id": f"quality-assessment-{digest[:24]}", "quality_assessment_sha256": digest, "dossier_mutated": False, "evidence_mutated": False, "connector_execution_performed": False}
    result = _record(ACTIONS[0], actor, event["quality_assessment_id"], event, ip_address)
    return {**result, "status": "collection_quality_assessed", "next_action": "review_dossier_contribution"}


def review_dossier_contribution(*, actor: str, quality_assessment_id: str, decision: str, rationale: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    assessment = find_assessment(quality_assessment_id)
    decision = str(decision or "").strip()
    rationale = str(rationale or "").strip()
    if assessment is None:
        return blocked("quality_assessment_required")
    if latest_contribution_review(quality_assessment_id) is not None:
        return blocked("dossier_contribution_already_reviewed")
    if confirmed is not True:
        return blocked("explicit_dossier_contribution_confirmation_required")
    if decision not in {"approved", "held", "rejected"}:
        return blocked("dossier_contribution_decision_invalid")
    if not rationale:
        return blocked("review_rationale_required")
    if decision == "approved" and assessment.get("artifact_state") != "accepted":
        return blocked("accepted_artifact_required")
    if decision == "approved" and int(assessment.get("observation_count") or 0) < 1:
        return blocked("derived_observation_required")
    if decision == "approved" and assessment.get("trust_tier") not in {"supported", "trusted"}:
        return blocked("supported_or_trusted_assessment_required")
    binding = {"quality_assessment_id": quality_assessment_id, "quality_assessment_sha256": assessment.get("quality_assessment_sha256"), "artifact_id": assessment.get("artifact_id"), "case_id": assessment.get("case_id"), "entity_id": assessment.get("entity_id")}
    content = {"event_type": "dossier_contribution_reviewed", "quality_assessment_id": quality_assessment_id, "artifact_id": assessment.get("artifact_id"), "case_id": assessment.get("case_id"), "entity_id": assessment.get("entity_id"), "decision": decision, "rationale": rationale, "quality_binding": binding, "quality_binding_sha256": _sha(binding)}
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "dossier_contribution_review_id": f"dossier-contribution-review-{digest[:24]}", "dossier_contribution_review_sha256": digest, "human_review_complete": True, "dossier_mutated": False, "evidence_mutated": False, "connector_execution_performed": False}
    result = _record(ACTIONS[1], actor, event["dossier_contribution_review_id"], event, ip_address)
    return {**result, "status": "dossier_contribution_reviewed", "next_action": "contribute_to_dossier_pipeline" if decision == "approved" else "resolve_quality_findings"}
