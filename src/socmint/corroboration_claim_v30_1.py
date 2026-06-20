from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.corroboration_claim.v30_1"
VERSION = "v30.1.0"
CREATE_ACTION = "corroboration_claim_created"
STATE_ACTION = "corroboration_claim_state_changed"
CLAIM_STATES = ("proposed", "withdrawn")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }


def claim_history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((CREATE_ACTION, STATE_ACTION)))
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


def current_claims() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for event in claim_history():
        claim_id = str(event.get("claim_id") or "")
        if not claim_id:
            continue
        histories.setdefault(claim_id, []).append(event)
        if event.get("event_type") == CREATE_ACTION:
            current[claim_id] = dict(event)
        elif claim_id in current:
            current[claim_id]["claim_state"] = event.get("to_state")
            current[claim_id]["latest_state_reason"] = event.get("reason")
            current[claim_id]["latest_state_sha256"] = event.get("claim_state_event_sha256")
    for claim_id, item in current.items():
        item["state_history"] = histories.get(claim_id, [])
    return sorted(current.values(), key=lambda item: str(item.get("claim_id")))


def find_claim(claim_id: str) -> dict[str, Any] | None:
    return next((item for item in current_claims() if item.get("claim_id") == claim_id), None)


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
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def create_corroboration_claim(
    *,
    actor: str,
    case_id: str,
    entity_id: str,
    claim_type: str,
    normalized_value: str,
    purpose: str,
    source_refs: list[dict[str, Any]] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    entity_id = str(entity_id or "").strip()
    claim_type = str(claim_type or "").strip()
    normalized_value = str(normalized_value or "").strip()
    purpose = str(purpose or "").strip()
    reason = str(reason or "").strip()
    refs = source_refs if isinstance(source_refs, list) else []

    if confirmed is not True:
        return blocked("explicit_claim_confirmation_required")
    if not case_id:
        return blocked("case_id_required")
    if not entity_id:
        return blocked("entity_id_required")
    if not claim_type:
        return blocked("claim_type_required")
    if not normalized_value:
        return blocked("normalized_value_required")
    if not purpose:
        return blocked("analytic_purpose_required")
    if not reason:
        return blocked("administrative_reason_required")
    if not refs:
        return blocked("source_reference_required")
    if any(not isinstance(ref, dict) or not str(ref.get("source_type") or "").strip() or not str(ref.get("source_id") or "").strip() for ref in refs):
        return blocked("source_reference_invalid")

    canonical_refs = sorted(
        [
            {
                "source_type": str(ref.get("source_type")).strip(),
                "source_id": str(ref.get("source_id")).strip(),
                "source_sha256": str(ref.get("source_sha256") or "").strip() or None,
            }
            for ref in refs
        ],
        key=lambda ref: (ref["source_type"], ref["source_id"]),
    )
    source_binding_sha256 = _sha(canonical_refs)
    identity = {
        "case_id": case_id,
        "entity_id": entity_id,
        "claim_type": claim_type,
        "normalized_value": normalized_value,
        "purpose": purpose,
        "source_binding_sha256": source_binding_sha256,
    }
    digest = _sha(identity)
    claim_id = f"corroboration-claim-{digest[:24]}"
    if find_claim(claim_id) is not None:
        return blocked("corroboration_claim_already_exists")

    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": CREATE_ACTION,
        "claim_id": claim_id,
        "case_id": case_id,
        "entity_id": entity_id,
        "claim_type": claim_type,
        "normalized_value": normalized_value,
        "purpose": purpose,
        "source_refs": canonical_refs,
        "source_binding_sha256": source_binding_sha256,
        "claim_state": "proposed",
        "reason": reason,
        "truth_assigned": False,
        "confidence_assigned": False,
        "human_review_complete": False,
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    event["claim_event_sha256"] = _sha(event)
    result = _record(CREATE_ACTION, actor, claim_id, event, ip_address)
    return {**result, "status": "corroboration_claim_created", "next_action": "bind_claim_evidence_and_observations"}


def change_claim_state(
    *,
    actor: str,
    claim_id: str,
    to_state: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    claim = find_claim(claim_id)
    to_state = str(to_state or "").strip()
    reason = str(reason or "").strip()
    if claim is None:
        return blocked("corroboration_claim_required")
    if confirmed is not True:
        return blocked("explicit_claim_state_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")
    if to_state != "withdrawn":
        return blocked("claim_state_transition_invalid")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")

    binding = {
        "claim_id": claim_id,
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "from_state": claim.get("claim_state"),
        "to_state": to_state,
    }
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": STATE_ACTION,
        "claim_id": claim_id,
        "from_state": claim.get("claim_state"),
        "to_state": to_state,
        "claim_binding": binding,
        "claim_binding_sha256": _sha(binding),
        "reason": reason,
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    event["claim_state_event_sha256"] = _sha(event)
    result = _record(STATE_ACTION, actor, claim_id, event, ip_address)
    return {**result, "status": "corroboration_claim_state_changed", "next_action": "retain_claim_history"}
