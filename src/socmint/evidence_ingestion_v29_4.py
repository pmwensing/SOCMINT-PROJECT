from __future__ import annotations

import re
from typing import Any

from . import database
from .collection_job_contract_v29_1 import find_contract
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.evidence_safe_ingestion.v29_4"
VERSION = "v29.4.0"
ACTIONS = (
    "evidence_artifact_registered",
    "evidence_artifact_state_changed",
    "evidence_observation_derived",
)
ARTIFACT_STATES = ("registered", "accepted", "quarantined", "rejected")
STATE_TRANSITIONS = {
    "registered": {"accepted", "quarantined", "rejected"},
    "quarantined": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": set(),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "raw_content_recorded": False,
        "legacy_evidence_mutated": False,
        "connector_output_mutated": False,
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
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "source_action": action,
            "audit_target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_artifacts() -> list[dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for event in history():
        artifact_id = str(event.get("artifact_id") or "")
        if not artifact_id:
            continue
        event_type = event.get("event_type")
        if event_type == "artifact_registered":
            artifacts[artifact_id] = {
                **event,
                "artifact_state": event.get("initial_state") or "registered",
                "state_history": [],
                "observation_count": 0,
            }
        elif artifact_id in artifacts and event_type == "artifact_state_changed":
            item = dict(artifacts[artifact_id])
            item["artifact_state"] = event.get("to_state")
            item["state_history"] = [*item.get("state_history", []), event]
            artifacts[artifact_id] = item
        elif artifact_id in artifacts and event_type == "observation_derived":
            item = dict(artifacts[artifact_id])
            item["observation_count"] = int(item.get("observation_count") or 0) + 1
            artifacts[artifact_id] = item
    return sorted(artifacts.values(), key=lambda item: str(item.get("recorded_at") or ""), reverse=True)


def find_artifact(artifact_id: str) -> dict[str, Any] | None:
    return next((item for item in current_artifacts() if item.get("artifact_id") == artifact_id), None)


def observations() -> list[dict[str, Any]]:
    return [item for item in history() if item.get("event_type") == "observation_derived"]


def _duplicate_for(content_sha256: str) -> dict[str, Any] | None:
    return next((item for item in current_artifacts() if item.get("content_sha256") == content_sha256), None)


def register_artifact(*, actor: str, collection_job_id: str, attempt_number: int, source_reference: str, acquired_at: str, content_sha256: str, content_type: str, byte_size: int, acquisition_method: str, provenance_metadata: Any, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    if contract.get("current_state") not in {"running", "completed"}:
        return blocked("running_or_completed_collection_job_required")
    try:
        attempt_number = int(attempt_number)
        byte_size = int(byte_size)
    except (TypeError, ValueError):
        return blocked("numeric_artifact_metadata_invalid")
    source_reference = str(source_reference or "").strip()
    acquired_at = str(acquired_at or "").strip()
    content_sha256 = str(content_sha256 or "").strip().lower()
    content_type = str(content_type or "").strip()
    acquisition_method = str(acquisition_method or "").strip()
    reason = str(reason or "").strip()
    provenance = provenance_metadata if isinstance(provenance_metadata, dict) else {}
    if confirmed is not True:
        return blocked("explicit_artifact_registration_confirmation_required")
    if attempt_number != int(contract.get("attempt_number") or 1):
        return blocked("collection_attempt_binding_mismatch")
    if not source_reference or not acquired_at or not acquisition_method:
        return blocked("acquisition_provenance_required")
    if not _SHA256.fullmatch(content_sha256):
        return blocked("content_sha256_invalid")
    if not content_type or byte_size < 0:
        return blocked("artifact_metadata_required")
    if not reason:
        return blocked("administrative_reason_required")
    duplicate = _duplicate_for(content_sha256)
    contract_binding = {
        "collection_job_id": collection_job_id,
        "collection_job_event_sha256": (contract.get("transition_history") or [contract])[-1].get("collection_job_event_sha256"),
        "attempt_number": attempt_number,
        "case_id": contract.get("case_id"),
        "entity_id": contract.get("entity_id"),
        "source_id": contract.get("source_id"),
        "authorization_binding": contract.get("authorization_binding"),
    }
    acquisition = {
        "source_reference": source_reference,
        "acquired_at": acquired_at,
        "acquisition_method": acquisition_method,
        "content_type": content_type,
        "byte_size": byte_size,
        "provenance_metadata": provenance,
    }
    initial_state = "quarantined" if duplicate else "registered"
    content = {
        "event_type": "artifact_registered",
        "collection_job_id": collection_job_id,
        "attempt_number": attempt_number,
        "contract_binding": contract_binding,
        "contract_binding_sha256": _sha(contract_binding),
        "content_sha256": content_sha256,
        "acquisition": acquisition,
        "acquisition_sha256": _sha(acquisition),
        "duplicate_of_artifact_id": duplicate.get("artifact_id") if duplicate else None,
        "initial_state": initial_state,
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "artifact_id": f"evidence-artifact-{digest[:24]}",
        "artifact_event_id": f"evidence-artifact-event-{digest[:24]}",
        "artifact_event_sha256": digest,
        "chain_of_custody_complete": True,
        "raw_content_recorded": False,
        "legacy_evidence_mutated": False,
        "connector_output_mutated": False,
        "connector_execution_performed": False,
    }
    result = _record(ACTIONS[0], actor, event["artifact_id"], event, ip_address)
    next_action = "review_duplicate_artifact" if duplicate else "review_artifact_acceptance"
    return {**result, "status": "evidence_artifact_registered", "next_action": next_action}


def change_artifact_state(*, actor: str, artifact_id: str, to_state: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    artifact = find_artifact(artifact_id)
    if artifact is None:
        return blocked("evidence_artifact_required")
    current_state = str(artifact.get("artifact_state") or "registered")
    to_state = str(to_state or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_artifact_state_confirmation_required")
    if to_state not in ARTIFACT_STATES:
        return blocked("artifact_state_invalid")
    if to_state not in STATE_TRANSITIONS.get(current_state, set()):
        return blocked("artifact_state_transition_invalid")
    if not reason:
        return blocked("state_change_reason_required")
    binding = {
        "artifact_id": artifact_id,
        "artifact_event_id": (artifact.get("state_history") or [artifact])[-1].get("artifact_event_id"),
        "artifact_event_sha256": (artifact.get("state_history") or [artifact])[-1].get("artifact_event_sha256"),
        "content_sha256": artifact.get("content_sha256"),
        "current_state": current_state,
    }
    content = {
        "event_type": "artifact_state_changed",
        "artifact_id": artifact_id,
        "from_state": current_state,
        "to_state": to_state,
        "artifact_binding": binding,
        "artifact_binding_sha256": _sha(binding),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "artifact_event_id": f"evidence-artifact-event-{digest[:24]}",
        "artifact_event_sha256": digest,
        "prior_artifact_event_mutated": False,
        "legacy_evidence_mutated": False,
        "connector_output_mutated": False,
    }
    result = _record(ACTIONS[1], actor, artifact_id, event, ip_address)
    return {**result, "status": "evidence_artifact_state_changed", "next_action": "derive_observations" if to_state == "accepted" else "review_artifact_state"}


def derive_observation(*, actor: str, artifact_id: str, observation_type: str, normalized_value: Any, confidence: str, derivation_method: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    artifact = find_artifact(artifact_id)
    if artifact is None:
        return blocked("evidence_artifact_required")
    if artifact.get("artifact_state") != "accepted":
        return blocked("accepted_evidence_artifact_required")
    observation_type = str(observation_type or "").strip()
    derivation_method = str(derivation_method or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_observation_derivation_confirmation_required")
    if not observation_type or normalized_value in (None, "") or not derivation_method:
        return blocked("observation_derivation_metadata_required")
    if not reason:
        return blocked("administrative_reason_required")
    artifact_binding = {
        "artifact_id": artifact_id,
        "content_sha256": artifact.get("content_sha256"),
        "acquisition_sha256": artifact.get("acquisition_sha256"),
        "artifact_event_sha256": (artifact.get("state_history") or [artifact])[-1].get("artifact_event_sha256"),
        "collection_job_id": artifact.get("collection_job_id"),
        "attempt_number": artifact.get("attempt_number"),
    }
    observation = {
        "observation_type": observation_type,
        "normalized_value": normalized_value,
        "confidence": str(confidence or "0.5"),
        "derivation_method": derivation_method,
    }
    content = {
        "event_type": "observation_derived",
        "artifact_id": artifact_id,
        "artifact_binding": artifact_binding,
        "artifact_binding_sha256": _sha(artifact_binding),
        "observation": observation,
        "observation_sha256": _sha(observation),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "observation_id": f"evidence-observation-{digest[:24]}",
        "artifact_event_id": f"evidence-artifact-event-{digest[:24]}",
        "artifact_event_sha256": digest,
        "raw_artifact_mutated": False,
        "legacy_evidence_mutated": False,
        "connector_output_mutated": False,
    }
    result = _record(ACTIONS[2], actor, artifact_id, event, ip_address)
    return {**result, "status": "evidence_observation_derived", "next_action": "review_observation_for_dossier"}
