from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.collection_job_contract.v29_1"
VERSION = "v29.1.0"
ACTIONS = (
    "collection_job_contract_created",
    "collection_job_transitioned",
)
STATES = (
    "drafted",
    "authorized",
    "queued",
    "running",
    "completed",
    "failed",
    "blocked",
    "cancelled",
    "superseded",
)
TERMINAL_STATES = {"completed", "cancelled", "superseded"}
FAILURE_STATES = {"failed", "blocked"}
TRANSITIONS = {
    "drafted": {"authorized", "cancelled", "superseded"},
    "authorized": {"queued", "cancelled", "superseded"},
    "queued": {"running", "blocked", "cancelled", "superseded"},
    "running": {"completed", "failed", "blocked", "cancelled", "superseded"},
    "failed": {"queued", "cancelled", "superseded"},
    "blocked": {"authorized", "queued", "cancelled", "superseded"},
    "completed": {"superseded"},
    "cancelled": set(),
    "superseded": set(),
}
FAILURE_CATEGORIES = (
    "authorization",
    "scope",
    "rate_limit",
    "network",
    "connector",
    "parsing",
    "provenance",
    "duplicate",
    "policy",
    "operator",
    "unknown",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "legacy_scan_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
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
                "target_value": row.target_value,
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
            "target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_contracts() -> list[dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for event in history():
        contract_id = str(event.get("collection_job_id") or "")
        if not contract_id:
            continue
        if event.get("event_type") == "collection_job_contract_created":
            contracts[contract_id] = {
                **event,
                "current_state": "drafted",
                "attempt_number": 1,
                "transition_history": [],
            }
        elif event.get("event_type") == "collection_job_transitioned" and contract_id in contracts:
            current = dict(contracts[contract_id])
            current["current_state"] = event.get("to_state")
            current["attempt_number"] = event.get("attempt_number")
            current["failure_category"] = event.get("failure_category")
            current["retry_eligible"] = event.get("retry_eligible")
            current["transition_history"] = [*current.get("transition_history", []), event]
            contracts[contract_id] = current
    return sorted(contracts.values(), key=lambda item: str(item.get("recorded_at") or ""), reverse=True)


def find_contract(collection_job_id: str) -> dict[str, Any] | None:
    return next((item for item in current_contracts() if item.get("collection_job_id") == collection_job_id), None)


def create_collection_job_contract(*, actor: str, connector: str, target_value: str, target_type: str, case_id: str, entity_id: str, source_id: str, authorization_binding: Any, purpose: str, idempotency_key: str, legacy_scan_job_id: int | None, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    connector = str(connector or "").strip()
    target_value = str(target_value or "").strip()
    target_type = str(target_type or "").strip()
    purpose = str(purpose or "").strip()
    idempotency_key = str(idempotency_key or "").strip()
    reason = str(reason or "").strip()
    authorization = authorization_binding if isinstance(authorization_binding, dict) else {}
    if confirmed is not True:
        return blocked("explicit_collection_job_creation_confirmation_required")
    if not connector:
        return blocked("connector_required")
    if not target_value or not target_type:
        return blocked("target_binding_required")
    if not purpose:
        return blocked("collection_purpose_required")
    if not authorization:
        return blocked("authorization_binding_required")
    if not idempotency_key:
        return blocked("idempotency_key_required")
    if not reason:
        return blocked("administrative_reason_required")
    for item in current_contracts():
        if item.get("idempotency_key") == idempotency_key and item.get("current_state") not in TERMINAL_STATES:
            return blocked("active_idempotency_key_must_be_unique")
    definition = {
        "connector": connector,
        "target_value": target_value,
        "target_type": target_type,
        "case_id": str(case_id or "").strip() or None,
        "entity_id": str(entity_id or "").strip() or None,
        "source_id": str(source_id or "").strip() or None,
        "authorization_binding": authorization,
        "purpose": purpose,
        "idempotency_key": idempotency_key,
        "legacy_scan_job_id": legacy_scan_job_id,
    }
    content = {
        "event_type": "collection_job_contract_created",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "initial_state": "drafted",
        "attempt_number": 1,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        **definition,
        "collection_job_id": f"collection-job-{digest[:24]}",
        "collection_job_event_id": f"collection-job-event-{digest[:24]}",
        "collection_job_event_sha256": digest,
        "legacy_scan_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[0], actor, event["collection_job_id"], event, ip_address)
    return {**result, "status": "collection_job_contract_created", "next_action": "authorize_collection_job"}


def transition_collection_job(*, collection_job_id: str, actor: str, to_state: str, authorization_binding: Any, failure_category: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    to_state = str(to_state or "").strip()
    reason = str(reason or "").strip()
    authorization = authorization_binding if isinstance(authorization_binding, dict) else None
    current_state = str(contract.get("current_state") or "drafted")
    if confirmed is not True:
        return blocked("explicit_collection_job_transition_confirmation_required")
    if to_state not in STATES:
        return blocked("collection_job_state_invalid")
    if to_state not in TRANSITIONS.get(current_state, set()):
        return blocked("collection_job_transition_invalid")
    if not reason:
        return blocked("transition_reason_required")
    if to_state == "authorized" and not authorization:
        return blocked("authorization_binding_required")
    if to_state in FAILURE_STATES and failure_category not in FAILURE_CATEGORIES:
        return blocked("failure_category_required")
    if to_state not in FAILURE_STATES:
        failure_category = ""
    retry_transition = current_state in FAILURE_STATES and to_state == "queued"
    attempt_number = int(contract.get("attempt_number") or 1) + (1 if retry_transition else 0)
    retry_eligible = to_state in FAILURE_STATES and failure_category not in {"authorization", "scope", "policy", "duplicate"}
    previous_binding = {
        "collection_job_id": collection_job_id,
        "current_state": current_state,
        "attempt_number": contract.get("attempt_number"),
        "last_event_sha256": (contract.get("transition_history") or [contract])[-1].get("collection_job_event_sha256"),
    }
    content = {
        "event_type": "collection_job_transitioned",
        "collection_job_id": collection_job_id,
        "from_state": current_state,
        "to_state": to_state,
        "attempt_number": attempt_number,
        "authorization_binding": authorization,
        "failure_category": failure_category or None,
        "retry_eligible": retry_eligible,
        "reason": reason,
        "previous_binding": previous_binding,
        "previous_binding_sha256": _sha(previous_binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "collection_job_event_id": f"collection-job-event-{digest[:24]}",
        "collection_job_event_sha256": digest,
        "prior_collection_job_event_mutated": False,
        "legacy_scan_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[1], actor, collection_job_id, event, ip_address)
    next_action = {
        "authorized": "queue_collection_job",
        "queued": "dispatch_collection_job_separately",
        "running": "monitor_collection_job",
        "completed": "review_collection_outputs",
        "failed": "review_retry_eligibility",
        "blocked": "resolve_collection_blocker",
        "cancelled": "review_collection_history",
        "superseded": "review_replacement_collection_job",
    }.get(to_state, "review_collection_job")
    return {**result, "status": "collection_job_transitioned", "next_action": next_action}
