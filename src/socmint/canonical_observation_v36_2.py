from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import observations
from .source_registry_v36_1 import find_source

SCHEMA = "socmint.canonical_observation.v36_2"
VERSION = "v36.2.0"
REGISTER_ACTION = "canonical_observation_registered"
STATE_ACTION = "canonical_observation_state_changed"
ADAPTER_FORMATS = ("json", "csv", "ndjson", "manual")
STATES = ("accepted", "quarantined", "rejected")
STATE_TRANSITIONS = {
    "accepted": set(),
    "quarantined": {"accepted", "rejected"},
    "rejected": set(),
}


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "truth_assigned": False,
        "identity_assigned": False,
        "source_observation_mutated": False,
        "artifact_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((REGISTER_ACTION, STATE_ACTION)))
            .order_by(
                database.AuditLog.created_at.asc(),
                database.AuditLog.id.asc(),
            )
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "recorded_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
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
            "recorded_at": (
                row.created_at.isoformat() if row.created_at else None
            ),
        }
    finally:
        session.close()


def _required(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        {
            str(item).strip()
            for item in value
            if str(item or "").strip()
        }
    )


def _parse_time(value: Any, *, required: bool) -> datetime | None:
    raw = _required(value)
    if not raw:
        return None if not required else None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _authoritative_observation(observation_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in observations()
            if item.get("observation_id") == observation_id
        ),
        None,
    )


def current_observations() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        observation_id = str(event.get("canonical_observation_id") or "")
        if not observation_id:
            continue
        if event.get("event_type") == REGISTER_ACTION:
            current[observation_id] = {
                **event,
                "observation_state": event.get("initial_state"),
                "state_history": [],
            }
        elif event.get("event_type") == STATE_ACTION and observation_id in current:
            item = dict(current[observation_id])
            item["observation_state"] = event.get("to_state")
            item["state_history"] = [*item.get("state_history", []), event]
            current[observation_id] = item
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_canonical_observation(
    canonical_observation_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_observations()
            if item.get("canonical_observation_id")
            == canonical_observation_id
        ),
        None,
    )


def register_canonical_observation(
    *,
    actor: str,
    case_id: str,
    source_id: str,
    source_observation_id: str,
    tool_run_id: str,
    artifact_id: str,
    observation_type: str,
    raw_value: Any,
    normalized_value: Any,
    observed_at: str,
    valid_time_start: str | None,
    valid_time_end: str | None,
    extraction_method: str,
    extraction_confidence: float,
    context: dict[str, Any] | None,
    parent_observation_id: str | None,
    adapter_format: str,
    adapter_name: str,
    adapter_version: str,
    quarantine_reasons: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    source_id = _required(source_id)
    source_observation_id = _required(source_observation_id)
    tool_run_id = _required(tool_run_id)
    artifact_id = _required(artifact_id)
    observation_type = _required(observation_type)
    extraction_method = _required(extraction_method)
    parent_observation_id = _required(parent_observation_id) or None
    adapter_format = _required(adapter_format).lower()
    adapter_name = _required(adapter_name)
    adapter_version = _required(adapter_version)
    quarantine_reasons = _string_list(quarantine_reasons)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_canonical_observation_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id:
        return blocked("case_id_required")
    if not source_id:
        return blocked("source_id_required")
    if not source_observation_id:
        return blocked("source_observation_id_required")
    if not tool_run_id or not artifact_id:
        return blocked("tool_run_and_artifact_binding_required")
    if not observation_type:
        return blocked("observation_type_required")
    if raw_value in (None, "") or normalized_value in (None, ""):
        return blocked("raw_and_normalized_values_required")
    if not extraction_method:
        return blocked("extraction_method_required")
    if not isinstance(context, dict):
        return blocked("observation_context_object_required")
    if adapter_format not in ADAPTER_FORMATS:
        return blocked("adapter_format_invalid")
    if not adapter_name or not adapter_version:
        return blocked("adapter_identity_required")
    if not reason:
        return blocked("administrative_reason_required")
    try:
        confidence = float(extraction_confidence)
    except (TypeError, ValueError):
        return blocked("extraction_confidence_invalid")
    if confidence < 0.0 or confidence > 1.0:
        return blocked("extraction_confidence_invalid")

    observed = _parse_time(observed_at, required=True)
    valid_start = _parse_time(valid_time_start, required=False)
    valid_end = _parse_time(valid_time_end, required=False)
    if observed is None:
        return blocked("observed_at_invalid")
    if valid_time_start and valid_start is None:
        return blocked("valid_time_start_invalid")
    if valid_time_end and valid_end is None:
        return blocked("valid_time_end_invalid")
    if valid_start and valid_end and valid_end < valid_start:
        return blocked("valid_time_range_invalid")

    source = find_source(source_id)
    if source is None:
        return blocked("source_record_required")
    if str(source.get("case_id") or "") != case_id:
        return blocked("observation_source_case_mismatch")
    capture = source.get("capture") or {}
    if not isinstance(capture, dict):
        return blocked("source_capture_binding_required")
    if str(capture.get("capture_artifact_id") or "") != artifact_id:
        return blocked("observation_source_artifact_mismatch")
    artifact_binding = capture.get("artifact_binding") or {}
    if not isinstance(artifact_binding, dict):
        return blocked("source_artifact_binding_required")
    if str(artifact_binding.get("collection_job_id") or "") != tool_run_id:
        return blocked("observation_source_tool_run_mismatch")

    authoritative = _authoritative_observation(source_observation_id)
    if authoritative is None:
        return blocked("authoritative_observation_required")
    if str(authoritative.get("artifact_id") or "") != artifact_id:
        return blocked("authoritative_observation_artifact_mismatch")
    authoritative_binding = authoritative.get("artifact_binding") or {}
    if not isinstance(authoritative_binding, dict):
        return blocked("authoritative_observation_binding_required")
    if str(authoritative_binding.get("collection_job_id") or "") != tool_run_id:
        return blocked("authoritative_observation_tool_run_mismatch")

    parent = None
    if parent_observation_id:
        parent = find_canonical_observation(parent_observation_id)
        if parent is None:
            return blocked("parent_canonical_observation_required")
        if str(parent.get("case_id") or "") != case_id:
            return blocked("parent_observation_case_mismatch")

    canonical_observation = {
        "observation_type": observation_type,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "observed_at": observed.isoformat(),
        "valid_time_start": valid_start.isoformat() if valid_start else None,
        "valid_time_end": valid_end.isoformat() if valid_end else None,
        "extraction_method": extraction_method,
        "extraction_confidence": confidence,
        "context": context,
        "parent_observation_id": parent_observation_id,
        "adapter_format": adapter_format,
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
    }
    source_binding = {
        "source_id": source_id,
        "source_event_sha256": source.get("source_event_sha256"),
        "capture_sha256": source.get("capture_sha256"),
        "artifact_id": artifact_id,
        "content_sha256": capture.get("content_sha256"),
        "tool_run_id": tool_run_id,
    }
    authoritative_binding = {
        "source_observation_id": source_observation_id,
        "observation_sha256": authoritative.get("observation_sha256"),
        "artifact_event_sha256": authoritative.get("artifact_event_sha256"),
        "source_observation": authoritative.get("observation"),
    }
    identity = {
        "case_id": case_id,
        "source_binding_sha256": _sha(source_binding),
        "authoritative_binding_sha256": _sha(authoritative_binding),
        "canonical_observation_sha256": _sha(canonical_observation),
    }
    canonical_observation_id = (
        f"canonical-observation-{_sha(identity)[:24]}"
    )
    if find_canonical_observation(canonical_observation_id) is not None:
        return blocked("canonical_observation_already_exists")

    validation_findings = list(quarantine_reasons)
    if confidence < 0.5:
        validation_findings.append("low_extraction_confidence")
    validation_findings = sorted(set(validation_findings))
    initial_state = "quarantined" if validation_findings else "accepted"
    content = {
        "event_type": REGISTER_ACTION,
        "canonical_observation_id": canonical_observation_id,
        "case_id": case_id,
        "source_id": source_id,
        "source_observation_id": source_observation_id,
        "tool_run_id": tool_run_id,
        "artifact_id": artifact_id,
        "canonical_observation": canonical_observation,
        "canonical_observation_sha256": _sha(canonical_observation),
        "source_binding": source_binding,
        "source_binding_sha256": _sha(source_binding),
        "authoritative_observation_binding": authoritative_binding,
        "authoritative_observation_binding_sha256": _sha(
            authoritative_binding
        ),
        "parent_binding_sha256": (
            parent.get("canonical_observation_event_sha256")
            if parent
            else None
        ),
        "initial_state": initial_state,
        "validation_findings": validation_findings,
        "reason": reason,
        "truth_assigned": False,
        "identity_assigned": False,
        "source_observation_mutated": False,
        "artifact_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "canonical_observation_event_id": (
            f"canonical-observation-event-{digest[:24]}"
        ),
        "canonical_observation_event_sha256": digest,
    }
    result = _record(
        REGISTER_ACTION,
        actor,
        canonical_observation_id,
        event,
        ip_address,
    )
    return {
        **result,
        "status": "canonical_observation_registered",
        "next_action": (
            "review_quarantined_observation"
            if initial_state == "quarantined"
            else "use_as_reviewable_observation"
        ),
    }


def change_canonical_observation_state(
    *,
    actor: str,
    canonical_observation_id: str,
    to_state: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    canonical_observation_id = _required(canonical_observation_id)
    to_state = _required(to_state)
    reason = _required(reason)
    current = find_canonical_observation(canonical_observation_id)
    if current is None:
        return blocked("canonical_observation_required")
    if confirmed is not True:
        return blocked("explicit_observation_state_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not reason:
        return blocked("administrative_reason_required")
    from_state = str(current.get("observation_state") or "")
    if to_state not in STATES:
        return blocked("canonical_observation_state_invalid")
    if to_state not in STATE_TRANSITIONS.get(from_state, set()):
        return blocked("canonical_observation_state_transition_invalid")

    content = {
        "event_type": STATE_ACTION,
        "canonical_observation_id": canonical_observation_id,
        "case_id": current.get("case_id"),
        "from_state": from_state,
        "to_state": to_state,
        "registration_event_sha256": current.get(
            "canonical_observation_event_sha256"
        ),
        "reason": reason,
        "truth_assigned": False,
        "identity_assigned": False,
        "source_observation_mutated": False,
        "artifact_mutated": False,
        "claim_created": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "canonical_observation_state_event_id": (
            f"canonical-observation-state-{digest[:24]}"
        ),
        "canonical_observation_state_event_sha256": digest,
    }
    result = _record(
        STATE_ACTION,
        actor,
        canonical_observation_id,
        event,
        ip_address,
    )
    return {
        **result,
        "status": "canonical_observation_state_changed",
        "next_action": (
            "use_as_reviewable_observation"
            if to_state == "accepted"
            else "retain_rejected_observation_history"
        ),
    }
