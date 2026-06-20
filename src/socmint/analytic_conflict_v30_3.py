from __future__ import annotations

from typing import Any

from . import database
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.analytic_conflict.v30_3"
VERSION = "v30.3.0"
CREATE_ACTION = "analytic_conflict_recorded"
RESOLVE_ACTION = "analytic_conflict_resolved"
CONFLICT_TYPES = ("contradiction", "analyst_disagreement")
RESOLUTIONS = ("unresolved", "both_retained", "claim_a_preferred", "claim_b_preferred", "insufficient_evidence")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "claim_mutated": False,
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }


def conflict_history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_((CREATE_ACTION, RESOLVE_ACTION)))
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


def current_conflicts() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for event in conflict_history():
        conflict_id = str(event.get("conflict_id") or "")
        if not conflict_id:
            continue
        histories.setdefault(conflict_id, []).append(event)
        if event.get("event_type") == CREATE_ACTION:
            current[conflict_id] = dict(event)
        elif event.get("event_type") == RESOLVE_ACTION and conflict_id in current:
            current[conflict_id]["resolution"] = event.get("resolution")
            current[conflict_id]["resolution_reason"] = event.get("reason")
            current[conflict_id]["resolved_by"] = event.get("actor")
            current[conflict_id]["resolution_event_sha256"] = event.get("resolution_event_sha256")
    for conflict_id, item in current.items():
        item["history"] = histories.get(conflict_id, [])
    return sorted(current.values(), key=lambda item: str(item.get("conflict_id")))


def find_conflict(conflict_id: str) -> dict[str, Any] | None:
    return next((item for item in current_conflicts() if item.get("conflict_id") == conflict_id), None)


def _record(action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(actor=actor, action=action, target_value=target, ip_address=ip_address, details=_canonical(event))
        session.add(row)
        session.commit()
        session.refresh(row)
        return {**event, "audit_record_id": row.id, "actor": actor, "recorded_at": row.created_at.isoformat() if row.created_at else None}
    finally:
        session.close()


def record_conflict(*, actor: str, conflict_type: str, claim_a_id: str, claim_b_id: str, disagreement_basis: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    conflict_type = str(conflict_type or "").strip()
    claim_a_id = str(claim_a_id or "").strip()
    claim_b_id = str(claim_b_id or "").strip()
    disagreement_basis = str(disagreement_basis or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_conflict_confirmation_required")
    if conflict_type not in CONFLICT_TYPES:
        return blocked("conflict_type_invalid")
    if not claim_a_id or not claim_b_id or claim_a_id == claim_b_id:
        return blocked("two_distinct_claims_required")
    if not disagreement_basis:
        return blocked("disagreement_basis_required")
    if not reason:
        return blocked("administrative_reason_required")
    claim_a = find_claim(claim_a_id)
    claim_b = find_claim(claim_b_id)
    if claim_a is None or claim_b is None:
        return blocked("corroboration_claim_required")
    if claim_a.get("case_id") != claim_b.get("case_id") or claim_a.get("entity_id") != claim_b.get("entity_id"):
        return blocked("claim_context_mismatch")
    if conflict_type == "contradiction":
        if claim_a.get("claim_type") != claim_b.get("claim_type"):
            return blocked("matching_claim_type_required")
        if claim_a.get("normalized_value") == claim_b.get("normalized_value"):
            return blocked("distinct_claim_values_required")

    ordered_claims = sorted([claim_a_id, claim_b_id])
    binding = {
        "case_id": claim_a.get("case_id"),
        "entity_id": claim_a.get("entity_id"),
        "claim_ids": ordered_claims,
        "claim_event_sha256": {
            claim_a_id: claim_a.get("claim_event_sha256"),
            claim_b_id: claim_b.get("claim_event_sha256"),
        },
        "conflict_type": conflict_type,
        "disagreement_basis": disagreement_basis,
    }
    digest = _sha(binding)
    conflict_id = f"analytic-conflict-{digest[:24]}"
    if find_conflict(conflict_id) is not None:
        return blocked("analytic_conflict_already_exists")
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": CREATE_ACTION,
        "conflict_id": conflict_id,
        "conflict_type": conflict_type,
        "case_id": claim_a.get("case_id"),
        "entity_id": claim_a.get("entity_id"),
        "claim_a_id": claim_a_id,
        "claim_b_id": claim_b_id,
        "claim_a_value": claim_a.get("normalized_value"),
        "claim_b_value": claim_b.get("normalized_value"),
        "conflict_binding": binding,
        "conflict_binding_sha256": digest,
        "disagreement_basis": disagreement_basis,
        "resolution": "unresolved",
        "reason": reason,
        "claim_mutated": False,
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    event["conflict_event_sha256"] = _sha(event)
    result = _record(CREATE_ACTION, actor, conflict_id, event, ip_address)
    return {**result, "status": "analytic_conflict_recorded", "next_action": "review_conflict_resolution"}


def resolve_conflict(*, actor: str, conflict_id: str, resolution: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    conflict = find_conflict(conflict_id)
    resolution = str(resolution or "").strip()
    reason = str(reason or "").strip()
    if conflict is None:
        return blocked("analytic_conflict_required")
    if conflict.get("resolution") != "unresolved":
        return blocked("unresolved_conflict_required")
    if confirmed is not True:
        return blocked("explicit_conflict_resolution_confirmation_required")
    if resolution not in set(RESOLUTIONS) - {"unresolved"}:
        return blocked("conflict_resolution_invalid")
    if not reason:
        return blocked("resolution_reason_required")
    binding = {
        "conflict_id": conflict_id,
        "conflict_event_sha256": conflict.get("conflict_event_sha256"),
        "resolution": resolution,
    }
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": RESOLVE_ACTION,
        "conflict_id": conflict_id,
        "resolution": resolution,
        "conflict_binding": binding,
        "conflict_binding_sha256": _sha(binding),
        "reason": reason,
        "prior_conflict_mutated": False,
        "claim_mutated": False,
        "evidence_mutated": False,
        "observation_mutated": False,
        "dossier_mutated": False,
    }
    event["resolution_event_sha256"] = _sha(event)
    result = _record(RESOLVE_ACTION, actor, conflict_id, event, ip_address)
    return {**result, "status": "analytic_conflict_resolved", "next_action": "assess_confidence_and_explainability"}
