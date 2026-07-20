from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import database
from .canonical_observation_v36_2 import find_canonical_observation
from .claim_verification_v36_5 import find_verification
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .source_registry_v36_1 import find_source

SCHEMA = "socmint.relationship_timeline.v36_6"
VERSION = "v36.6.0"
ACTION = "relationship_timeline_assessed"
RELATIONSHIP_TYPES = (
    "person_to_person",
    "person_to_organization",
    "organization_to_domain",
    "account_to_account",
    "communication",
    "event_association",
    "co_occurrence",
)
INFERENCE_CLASSES = (
    "direct_evidence",
    "supported_inference",
    "co_occurrence_only",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "relationship_asserted_as_truth": False,
        "causation_assigned": False,
        "graph_mutated": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _time(value: Any, *, required: bool = False) -> datetime | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    actor: str,
    assessment_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=assessment_id,
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


def current_relationship_assessments() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        key = str(event.get("relationship_timeline_assessment_id") or "")
        if key:
            current[key] = event
    return sorted(
        current.values(),
        key=lambda item: (
            str((item.get("times") or {}).get("event_time") or ""),
            str(item.get("relationship_timeline_assessment_id") or ""),
        ),
    )


def find_relationship_assessment(assessment_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_relationship_assessments()
            if item.get("relationship_timeline_assessment_id") == assessment_id
        ),
        None,
    )


def timeline_for_entity(entity_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in current_relationship_assessments()
        if entity_id in {item.get("subject_entity_id"), item.get("object_entity_id")}
    ]


def assess_relationship_timeline(
    *,
    actor: str,
    claim_id: str,
    relationship_type: str,
    subject_entity_id: str,
    object_entity_id: str,
    source_ids: list[str] | None,
    observation_ids: list[str] | None,
    event_time: str,
    report_time: str | None,
    capture_time: str,
    valid_from: str | None,
    valid_to: str | None,
    inference_class: str,
    inference_warning: str,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    claim_id = _required(claim_id)
    relationship_type = _required(relationship_type)
    subject_entity_id = _required(subject_entity_id)
    object_entity_id = _required(object_entity_id)
    inference_class = _required(inference_class)
    inference_warning = _required(inference_warning)
    reason = _required(reason)
    normalized_sources = sorted(
        {_required(item) for item in (source_ids or []) if _required(item)}
    )
    normalized_observations = sorted(
        {_required(item) for item in (observation_ids or []) if _required(item)}
    )
    normalized_limitations = sorted(
        {_required(item) for item in (limitations or []) if _required(item)}
    )
    if confirmed is not True:
        return blocked("explicit_relationship_assessment_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not claim_id:
        return blocked("claim_id_required")
    if relationship_type not in RELATIONSHIP_TYPES:
        return blocked("relationship_type_invalid")
    if not subject_entity_id or not object_entity_id:
        return blocked("relationship_entities_required")
    if subject_entity_id == object_entity_id:
        return blocked("relationship_entities_must_be_distinct")
    if not normalized_sources or not normalized_observations:
        return blocked("relationship_sources_and_observations_required")
    if inference_class not in INFERENCE_CLASSES:
        return blocked("relationship_inference_class_invalid")
    if not inference_warning or not reason:
        return blocked("inference_warning_and_reason_required")
    if relationship_type == "co_occurrence" and inference_class != "co_occurrence_only":
        return blocked("co_occurrence_must_remain_co_occurrence_only")
    if inference_class == "co_occurrence_only" and relationship_type != "co_occurrence":
        return blocked("co_occurrence_inference_requires_co_occurrence_type")

    event_value = _time(event_time, required=True)
    report_value = _time(report_time)
    capture_value = _time(capture_time, required=True)
    valid_from_value = _time(valid_from)
    valid_to_value = _time(valid_to)
    if event_value is None or capture_value is None:
        return blocked("event_and_capture_times_required")
    if report_time and report_value is None:
        return blocked("report_time_invalid")
    if valid_from and valid_from_value is None:
        return blocked("valid_from_invalid")
    if valid_to and valid_to_value is None:
        return blocked("valid_to_invalid")
    if valid_from_value and valid_to_value and valid_to_value < valid_from_value:
        return blocked("relationship_validity_range_invalid")
    if report_value and report_value < event_value:
        return blocked("report_time_precedes_event_time")
    if capture_value < event_value:
        return blocked("capture_time_precedes_event_time")

    claim = find_claim(claim_id)
    if claim is None or claim.get("claim_state") != "proposed":
        return blocked("proposed_corroboration_claim_required")
    verification = find_verification(claim_id)
    if verification is None:
        return blocked("claim_verification_required")
    case_id = str(claim.get("case_id") or "")
    source_bindings = []
    for source_id in normalized_sources:
        source = find_source(source_id)
        if source is None:
            return blocked("source_record_required")
        if str(source.get("case_id") or "") != case_id:
            return blocked("relationship_source_case_mismatch")
        source_bindings.append(
            {
                "source_id": source_id,
                "source_event_sha256": source.get("source_event_sha256"),
                "capture_sha256": source.get("capture_sha256"),
            }
        )
    observation_bindings = []
    for observation_id in normalized_observations:
        observation = find_canonical_observation(observation_id)
        if observation is None or observation.get("observation_state") != "accepted":
            return blocked("accepted_canonical_observation_required")
        if str(observation.get("case_id") or "") != case_id:
            return blocked("relationship_observation_case_mismatch")
        observation_bindings.append(
            {
                "canonical_observation_id": observation_id,
                "canonical_observation_event_sha256": observation.get(
                    "canonical_observation_event_sha256"
                ),
            }
        )

    times = {
        "event_time": event_value.isoformat(),
        "report_time": report_value.isoformat() if report_value else None,
        "capture_time": capture_value.isoformat(),
        "valid_from": valid_from_value.isoformat() if valid_from_value else None,
        "valid_to": valid_to_value.isoformat() if valid_to_value else None,
    }
    bindings = {
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "claim_verification_sha256": verification.get(
            "claim_verification_assessment_sha256"
        ),
        "source_bindings_sha256": _sha(source_bindings),
        "observation_bindings_sha256": _sha(observation_bindings),
    }
    content = {
        "event_type": ACTION,
        "case_id": case_id,
        "claim_id": claim_id,
        "relationship_type": relationship_type,
        "subject_entity_id": subject_entity_id,
        "object_entity_id": object_entity_id,
        "source_ids": normalized_sources,
        "observation_ids": normalized_observations,
        "source_bindings": source_bindings,
        "observation_bindings": observation_bindings,
        "times": times,
        "inference_class": inference_class,
        "inference_warning": inference_warning,
        "limitations": normalized_limitations,
        "bindings": bindings,
        "bindings_sha256": _sha(bindings),
        "reason": reason,
        "relationship_asserted_as_truth": False,
        "causation_assigned": False,
        "graph_mutated": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    assessment_id = f"relationship-timeline-{digest[:24]}"
    if find_relationship_assessment(assessment_id) is not None:
        return blocked("relationship_timeline_assessment_already_exists")
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "relationship_timeline_assessment_id": assessment_id,
        "relationship_timeline_assessment_sha256": digest,
    }
    result = _record(actor, assessment_id, event, ip_address)
    return {
        **result,
        "status": "relationship_timeline_assessed",
        "next_action": "retain_source_grounded_timeline_assessment",
    }
