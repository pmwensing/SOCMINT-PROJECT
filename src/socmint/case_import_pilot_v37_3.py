from __future__ import annotations

from typing import Any

from . import database
from .cases.entity_scope_filter import ScopeStatus, evaluate_text_scope
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_repo.location_map import EvidenceLocation, LocationType, validate_location
from .operational_import_record_projection_v37_2 import (
    find_staged_record_projection,
)
from .operational_import_v37_1 import find_import

SCHEMA = "socmint.case_import_pilot.v37_3"
VERSION = "v37.3.0"
PILOT_CASE_ID = "case_46_montreal"
ASSESS_ACTION = "case_import_scope_assessed"
DECISION_ACTION = "case_import_review_decision_recorded"
DECISIONS = ("accepted", "quarantined", "rejected")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
        "original_uploaded_to_github": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((ASSESS_ACTION, DECISION_ACTION)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str,
    actor: str,
    target: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
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
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _current(event_type: str, key_name: str) -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        if event.get("event_type") != event_type:
            continue
        key = str(event.get(key_name) or "")
        if key:
            current[key] = event
    return sorted(current.values(), key=lambda item: str(item.get(key_name) or ""))


def current_scope_assessments() -> list[dict[str, Any]]:
    return _current(ASSESS_ACTION, "staged_record_id")


def current_review_decisions() -> list[dict[str, Any]]:
    return _current(DECISION_ACTION, "staged_record_id")


def find_scope_assessment(staged_record_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in current_scope_assessments() if item.get("staged_record_id") == staged_record_id),
        None,
    )


def find_review_decision(staged_record_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in current_review_decisions() if item.get("staged_record_id") == staged_record_id),
        None,
    )


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return _required(value)


def assess_pilot_record(
    *,
    actor: str,
    staged_record_id: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    staged_record_id = _required(staged_record_id)
    reason = _required(reason)
    if confirmed is not True:
        return blocked("explicit_scope_assessment_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not staged_record_id:
        return blocked("staged_record_id_required")
    if not reason:
        return blocked("administrative_reason_required")

    staged = find_staged_record_projection(staged_record_id)
    if staged is None:
        return blocked("staged_import_record_required")
    import_id = _required(staged.get("operational_import_id"))
    parent = find_import(import_id)
    if parent is None:
        return blocked("operational_import_required")
    envelope = parent.get("envelope") or {}
    if not isinstance(envelope, dict) or envelope.get("case_id") != PILOT_CASE_ID:
        return blocked("controlled_pilot_case_required")

    scope_input = " ".join(
        _flatten(staged.get(key))
        for key in ("raw_value", "normalized_value", "context")
    )
    scope = evaluate_text_scope(scope_input)
    identity = {
        "staged_record_id": staged_record_id,
        "record_sha256": staged.get("record_sha256"),
        "scope_status": scope.status.value,
        "matched_terms": list(scope.matched_terms),
    }
    identity_sha = _sha(identity)
    existing = find_scope_assessment(staged_record_id)
    if existing is not None and existing.get("assessment_sha256") == identity_sha:
        return {
            **existing,
            "status": "case_import_scope_assessment_reused",
            "idempotent_replay": True,
            "next_action": "record_human_review_decision",
        }

    content = {
        "event_type": ASSESS_ACTION,
        "scope_assessment_id": f"case-import-scope-{identity_sha[:24]}",
        "case_id": PILOT_CASE_ID,
        "operational_import_id": import_id,
        "staged_record_id": staged_record_id,
        "record_sha256": staged.get("record_sha256"),
        "initial_record_state": staged.get("initial_state"),
        "scope_status": scope.status.value,
        "scope_reason": scope.reason,
        "matched_terms": list(scope.matched_terms),
        "relocation_context_only": scope.status == ScopeStatus.RELOCATION_CONTEXT,
        "out_of_scope": scope.status == ScopeStatus.OUT_OF_SCOPE,
        "candidate_review_required": scope.status == ScopeStatus.CANDIDATE_REVIEW_REQUIRED,
        "claim_support_allowed": False,
        "observation_promotion_allowed": False,
        "reason": reason,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "assessment_sha256": identity_sha,
        "scope_event_id": f"case-import-scope-event-{digest[:24]}",
        "scope_event_sha256": digest,
    }
    result = _record(ASSESS_ACTION, actor, staged_record_id, event, ip_address)
    return {
        **result,
        "status": "case_import_scope_assessed",
        "idempotent_replay": False,
        "next_action": "record_human_review_decision",
    }


def record_pilot_review_decision(
    *,
    actor: str,
    staged_record_id: str,
    decision: str,
    quarantine_resolution: str | None,
    candidate_resolution_reference: str | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    staged_record_id = _required(staged_record_id)
    decision = _required(decision).lower()
    quarantine_resolution = _required(quarantine_resolution) or None
    candidate_resolution_reference = _required(candidate_resolution_reference) or None
    reason = _required(reason)
    if confirmed is not True:
        return blocked("explicit_pilot_review_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if decision not in DECISIONS:
        return blocked("pilot_review_decision_invalid")
    if not reason:
        return blocked("administrative_reason_required")

    assessment = find_scope_assessment(staged_record_id)
    staged = find_staged_record_projection(staged_record_id)
    if assessment is None or staged is None:
        return blocked("scope_assessment_and_staged_record_required")
    scope_status = str(assessment.get("scope_status") or "")
    initial_state = str(staged.get("initial_state") or "")
    if initial_state == "duplicate" and decision != "rejected":
        return blocked("duplicate_record_must_be_rejected")
    if scope_status == ScopeStatus.OUT_OF_SCOPE.value and decision != "rejected":
        return blocked("out_of_scope_record_must_be_rejected")
    if (
        scope_status == ScopeStatus.CANDIDATE_REVIEW_REQUIRED.value
        and decision == "accepted"
        and not candidate_resolution_reference
    ):
        return blocked("candidate_resolution_reference_required")
    if initial_state == "quarantined" and decision == "accepted" and not quarantine_resolution:
        return blocked("quarantine_resolution_required")

    accepted = decision == "accepted"
    relocation_only = scope_status == ScopeStatus.RELOCATION_CONTEXT.value
    content = {
        "event_type": DECISION_ACTION,
        "case_id": PILOT_CASE_ID,
        "staged_record_id": staged_record_id,
        "scope_assessment_id": assessment.get("scope_assessment_id"),
        "scope_event_sha256": assessment.get("scope_event_sha256"),
        "record_sha256": staged.get("record_sha256"),
        "decision": decision,
        "quarantine_resolution": quarantine_resolution,
        "candidate_resolution_reference": candidate_resolution_reference,
        "relocation_context_only": relocation_only,
        "observation_promotion_allowed": accepted,
        "issue_claim_support_allowed": accepted and not relocation_only,
        "reason": reason,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "review_decision_id": f"case-import-review-{digest[:24]}",
        "review_decision_sha256": digest,
    }
    result = _record(DECISION_ACTION, actor, staged_record_id, event, ip_address)
    return {
        **result,
        "status": "case_import_review_decision_recorded",
        "next_action": "promote_reviewed_record_to_observation" if accepted else "retain_review_record",
    }


def build_evidence_location_projection(
    *,
    evidence_id: str,
    location_type: str,
    location_id: str,
    path_or_file_id: str,
    sha256: str,
    verified: bool,
    notes: str = "",
) -> dict[str, Any]:
    try:
        typed_location = LocationType(location_type)
    except ValueError:
        return blocked("evidence_location_type_invalid")
    entry = EvidenceLocation(
        evidence_id=_required(evidence_id),
        location_type=typed_location,
        location_id=_required(location_id),
        path_or_file_id=_required(path_or_file_id),
        sha256=_required(sha256).lower(),
        verified=bool(verified),
        notes=_required(notes),
    )
    try:
        validate_location(entry)
    except (ValueError, TypeError):
        return blocked("evidence_location_invalid")
    projection = {
        "evidence_id": entry.evidence_id,
        "location_type": entry.location_type.value,
        "location_id": entry.location_id,
        "path_or_file_id": entry.path_or_file_id,
        "sha256": entry.sha256,
        "verified": entry.verified,
        "notes": entry.notes,
        "original_uploaded_to_github": False,
        "manifest_projection_only": True,
    }
    return {
        "schema": "socmint.evidence_location_projection.v37_3",
        "version": VERSION,
        "status": "evidence_location_projection_ready",
        "projection": projection,
        "projection_sha256": _sha(projection),
        "original_uploaded_to_github": False,
    }
