from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import find_artifact

SCHEMA = "socmint.source_registry.v36_1"
VERSION = "v36.1.0"
REGISTER_ACTION = "source_record_registered"
RELIABILITY_ACTION = "source_reliability_assessed"
SOURCE_TYPES = (
    "first_party",
    "primary_record",
    "secondary",
    "aggregator",
    "archive",
    "api",
    "registry",
    "other",
)
ORIGIN_TYPES = ("original", "derived", "unknown")
ACCESS_METHODS = (
    "public_web",
    "public_api",
    "authorized_account",
    "archive",
    "file_import",
    "other",
)
RELIABILITY_BANDS = ("A", "B", "C", "D", "E", "U")
RELIABILITY_COMPONENTS = (
    "authority",
    "directness",
    "authenticity",
    "capture_integrity",
    "temporal_relevance",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "truth_assigned": False,
        "claim_approved": False,
        "artifact_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(
                database.AuditLog.action.in_(
                    (REGISTER_ACTION, RELIABILITY_ACTION)
                )
            )
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


def _valid_iso(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _normalize_url(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port_value = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    port = f":{port_value}" if port_value else ""
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(
        (
            parsed.scheme.lower(),
            f"{host}{port}",
            path,
            parsed.query,
            "",
        )
    )


def reliability_history(
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = [
        item
        for item in _history()
        if item.get("event_type") == RELIABILITY_ACTION
    ]
    if source_id is None:
        return rows
    return [item for item in rows if item.get("source_id") == source_id]


def current_reliability_profiles(
    source_id: str | None = None,
) -> list[dict[str, Any]]:
    current: dict[tuple[str, str], dict[str, Any]] = {}
    for event in reliability_history(source_id):
        key = (
            str(event.get("source_id") or ""),
            str(event.get("claim_type") or ""),
        )
        if all(key):
            current[key] = event
    return sorted(
        current.values(),
        key=lambda item: (
            str(item.get("source_id") or ""),
            str(item.get("claim_type") or ""),
        ),
    )


def current_sources() -> list[dict[str, Any]]:
    events = _history()
    registrations = [
        item for item in events if item.get("event_type") == REGISTER_ACTION
    ]
    profiles: dict[str, list[dict[str, Any]]] = {}
    current: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        if event.get("event_type") != RELIABILITY_ACTION:
            continue
        key = (
            str(event.get("source_id") or ""),
            str(event.get("claim_type") or ""),
        )
        if all(key):
            current[key] = event
    for assessment in current.values():
        profiles.setdefault(str(assessment.get("source_id") or ""), []).append(
            assessment
        )
    result = []
    for registration in registrations:
        source_id = str(registration.get("source_id") or "")
        source_profiles = sorted(
            profiles.get(source_id, []),
            key=lambda item: str(item.get("claim_type") or ""),
        )
        result.append(
            {
                **registration,
                "source_reliability_profile": source_profiles,
                "reliability_assessed": bool(source_profiles),
            }
        )
    return sorted(result, key=lambda item: str(item.get("source_id") or ""))


def find_source(source_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_sources()
            if item.get("source_id") == source_id
        ),
        None,
    )


def _artifact_binding(
    *,
    artifact: dict[str, Any],
    case_id: str,
    content_sha256: str,
) -> dict[str, Any] | None:
    if artifact.get("artifact_state") != "accepted":
        return None
    contract = artifact.get("contract_binding") or {}
    if not isinstance(contract, dict):
        return None
    if str(contract.get("case_id") or "") != case_id:
        return None
    if str(artifact.get("content_sha256") or "").lower() != content_sha256:
        return None
    latest = (artifact.get("state_history") or [artifact])[-1]
    return {
        "artifact_id": artifact.get("artifact_id"),
        "artifact_event_sha256": latest.get("artifact_event_sha256"),
        "content_sha256": artifact.get("content_sha256"),
        "acquisition_sha256": artifact.get("acquisition_sha256"),
        "collection_job_id": artifact.get("collection_job_id"),
        "case_id": contract.get("case_id"),
        "entity_id": contract.get("entity_id"),
    }


def register_source(
    *,
    actor: str,
    case_id: str,
    source_type: str,
    publisher_or_operator: str,
    canonical_url: str,
    retrieved_url: str,
    published_at: str | None,
    captured_at: str,
    jurisdiction: str,
    access_method: str,
    authentication_required: bool,
    authorization_reference: str | None,
    original_or_derived: str,
    terms_and_collection_notes: str,
    content_sha256: str,
    capture_artifact_id: str,
    adapter_name: str,
    adapter_version: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    source_type = _required(source_type)
    publisher_or_operator = _required(publisher_or_operator)
    normalized_canonical = _normalize_url(canonical_url)
    normalized_retrieved = _normalize_url(retrieved_url)
    published_at = _required(published_at) or None
    captured_at = _required(captured_at)
    jurisdiction = _required(jurisdiction)
    access_method = _required(access_method)
    authorization_reference = _required(authorization_reference) or None
    original_or_derived = _required(original_or_derived)
    notes = _required(terms_and_collection_notes)
    content_sha256 = _required(content_sha256).lower()
    capture_artifact_id = _required(capture_artifact_id)
    adapter_name = _required(adapter_name)
    adapter_version = _required(adapter_version)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_source_registration_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id:
        return blocked("case_id_required")
    if source_type not in SOURCE_TYPES:
        return blocked("source_type_invalid")
    if not publisher_or_operator:
        return blocked("publisher_or_operator_required")
    if normalized_canonical is None or normalized_retrieved is None:
        return blocked("source_url_invalid")
    if published_at is not None and not _valid_iso(published_at):
        return blocked("published_at_invalid")
    if not _valid_iso(captured_at):
        return blocked("captured_at_invalid")
    if not jurisdiction:
        return blocked("jurisdiction_required")
    if access_method not in ACCESS_METHODS:
        return blocked("access_method_invalid")
    if not isinstance(authentication_required, bool):
        return blocked("authentication_required_boolean_required")
    if authentication_required and not authorization_reference:
        return blocked("authenticated_access_authorization_reference_required")
    if access_method == "authorized_account" and not authorization_reference:
        return blocked("authorized_account_reference_required")
    if original_or_derived not in ORIGIN_TYPES:
        return blocked("original_or_derived_invalid")
    if not notes:
        return blocked("terms_and_collection_notes_required")
    if not _SHA256.fullmatch(content_sha256):
        return blocked("content_sha256_invalid")
    if not capture_artifact_id:
        return blocked("capture_artifact_id_required")
    if not adapter_name or not adapter_version:
        return blocked("adapter_identity_required")
    if not reason:
        return blocked("administrative_reason_required")

    artifact = find_artifact(capture_artifact_id)
    if artifact is None:
        return blocked("evidence_artifact_required")
    binding = _artifact_binding(
        artifact=artifact,
        case_id=case_id,
        content_sha256=content_sha256,
    )
    if binding is None:
        if artifact.get("artifact_state") != "accepted":
            return blocked("accepted_evidence_artifact_required")
        contract = artifact.get("contract_binding") or {}
        if str(contract.get("case_id") or "") != case_id:
            return blocked("source_case_artifact_binding_mismatch")
        return blocked("source_content_artifact_hash_mismatch")

    source_identity = {
        "case_id": case_id,
        "canonical_url": normalized_canonical,
        "retrieved_url": normalized_retrieved,
        "content_sha256": content_sha256,
        "capture_artifact_id": capture_artifact_id,
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
    }
    source_id = f"source-record-{_sha(source_identity)[:24]}"
    if find_source(source_id) is not None:
        return blocked("source_record_already_exists")

    capture = {
        "canonical_url": normalized_canonical,
        "retrieved_url": normalized_retrieved,
        "published_at": published_at,
        "captured_at": captured_at,
        "access_method": access_method,
        "authentication_required": authentication_required,
        "authorization_reference": authorization_reference,
        "terms_and_collection_notes": notes,
        "content_sha256": content_sha256,
        "capture_artifact_id": capture_artifact_id,
        "artifact_binding": binding,
        "artifact_binding_sha256": _sha(binding),
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
    }
    content = {
        "event_type": REGISTER_ACTION,
        "source_id": source_id,
        "case_id": case_id,
        "source_type": source_type,
        "publisher_or_operator": publisher_or_operator,
        "jurisdiction": jurisdiction,
        "original_or_derived": original_or_derived,
        "capture": capture,
        "capture_sha256": _sha(capture),
        "independence_group_id": None,
        "independence_assessed": False,
        "source_reliability_profile": [],
        "capture_integrity_verified": True,
        "reason": reason,
        "truth_assigned": False,
        "claim_approved": False,
        "artifact_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "source_event_id": f"source-record-event-{digest[:24]}",
        "source_event_sha256": digest,
    }
    result = _record(
        REGISTER_ACTION,
        actor,
        source_id,
        event,
        ip_address,
    )
    return {
        **result,
        "status": "source_record_registered",
        "next_action": "assess_claim_type_source_reliability",
    }


def assess_source_reliability(
    *,
    actor: str,
    source_id: str,
    claim_type: str,
    reliability_band: str,
    components: dict[str, Any] | None,
    reasons: list[str] | None,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    source_id = _required(source_id)
    claim_type = _required(claim_type)
    reliability_band = _required(reliability_band).upper()
    reason = _required(reason)
    reasons = _string_list(reasons)
    limitations = _string_list(limitations)
    component_input = components if isinstance(components, dict) else {}

    source = find_source(source_id)
    if source is None:
        return blocked("source_record_required")
    if confirmed is not True:
        return blocked("explicit_source_reliability_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not claim_type:
        return blocked("claim_type_required")
    if reliability_band not in RELIABILITY_BANDS:
        return blocked("source_reliability_band_invalid")
    if not reasons:
        return blocked("source_reliability_reasons_required")
    if not reason:
        return blocked("administrative_reason_required")

    normalized_components: dict[str, int] = {}
    for key in RELIABILITY_COMPONENTS:
        value = component_input.get(key)
        if isinstance(value, bool):
            return blocked("source_reliability_component_invalid")
        try:
            score = int(value)
        except (TypeError, ValueError):
            return blocked("source_reliability_component_invalid")
        if score < 0 or score > 100:
            return blocked("source_reliability_component_invalid")
        normalized_components[key] = score

    reliability_score = round(
        sum(normalized_components.values()) / len(RELIABILITY_COMPONENTS),
        1,
    )
    assessment = {
        "source_id": source_id,
        "source_event_sha256": source.get("source_event_sha256"),
        "claim_type": claim_type,
        "reliability_band": reliability_band,
        "reliability_score": reliability_score,
        "components": normalized_components,
        "reasons": reasons,
        "limitations": limitations,
    }
    assessment_id = f"source-reliability-{_sha(assessment)[:24]}"
    if any(
        item.get("source_reliability_assessment_id") == assessment_id
        for item in reliability_history(source_id)
    ):
        return blocked("source_reliability_assessment_already_exists")

    source_binding = {
        "source_id": source_id,
        "source_event_sha256": source.get("source_event_sha256"),
        "capture_sha256": source.get("capture_sha256"),
    }
    content = {
        "event_type": RELIABILITY_ACTION,
        "source_id": source_id,
        "case_id": source.get("case_id"),
        "claim_type": claim_type,
        "reliability_band": reliability_band,
        "reliability_score": reliability_score,
        "components": normalized_components,
        "reasons": reasons,
        "limitations": limitations,
        "source_binding": source_binding,
        "source_binding_sha256": _sha(source_binding),
        "reason": reason,
        "truth_assigned": False,
        "claim_approved": False,
        "artifact_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    event_digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "source_reliability_assessment_id": assessment_id,
        "source_reliability_assessment_sha256": event_digest,
    }
    result = _record(
        RELIABILITY_ACTION,
        actor,
        source_id,
        event,
        ip_address,
    )
    return {
        **result,
        "status": "source_reliability_assessed",
        "next_action": "retain_claim_type_specific_source_profile",
    }
