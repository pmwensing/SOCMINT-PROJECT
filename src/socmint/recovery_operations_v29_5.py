from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import database
from .collection_job_contract_v29_1 import find_contract, transition_collection_job
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.retry_recovery_operator_intervention.v29_5"
VERSION = "v29.5.0"
ACTIONS = (
    "collection_retry_requested",
    "collection_retry_decided",
    "collection_recovery_plan_created",
    "collection_operator_intervention_recorded",
)
REQUEST_STATES = ("pending", "approved", "denied", "superseded")
PLAN_TYPES = ("retry", "manual_review", "cancel", "supersede", "resolve_blocker")
INTERVENTION_TYPES = ("manual_review", "resolve_blocker", "cancel", "supersede", "quarantine_review")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "connector_execution_performed": False,
        "retry_execution_performed": False,
        "legacy_scan_job_mutated": False,
        "evidence_mutated": False,
    }


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


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


def current_retry_requests() -> list[dict[str, Any]]:
    requests: dict[str, dict[str, Any]] = {}
    for event in history():
        request_id = str(event.get("retry_request_id") or "")
        if not request_id:
            continue
        if event.get("event_type") == "retry_requested":
            requests[request_id] = {**event, "request_state": "pending", "decision": None}
        elif event.get("event_type") == "retry_decided" and request_id in requests:
            item = dict(requests[request_id])
            item["request_state"] = "approved" if event.get("approved") is True else "denied"
            item["decision"] = event
            requests[request_id] = item
    return sorted(requests.values(), key=lambda item: str(item.get("recorded_at") or ""), reverse=True)


def find_retry_request(retry_request_id: str) -> dict[str, Any] | None:
    return next((item for item in current_retry_requests() if item.get("retry_request_id") == retry_request_id), None)


def recovery_plans() -> list[dict[str, Any]]:
    return [item for item in history() if item.get("event_type") == "recovery_plan_created"]


def interventions() -> list[dict[str, Any]]:
    return [item for item in history() if item.get("event_type") == "operator_intervention_recorded"]


def request_retry(*, actor: str, collection_job_id: str, idempotency_key: str, backoff_seconds: int, earliest_retry_at: str, retry_window_ends_at: str, max_attempts: int, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    if contract.get("current_state") not in {"failed", "blocked"}:
        return blocked("failed_or_blocked_collection_job_required")
    if contract.get("retry_eligible") is not True:
        return blocked("collection_job_not_retry_eligible")
    if confirmed is not True:
        return blocked("explicit_retry_request_confirmation_required")
    reason = str(reason or "").strip()
    idempotency_key = str(idempotency_key or "").strip()
    if not reason:
        return blocked("retry_reason_required")
    if not idempotency_key:
        return blocked("retry_idempotency_key_required")
    try:
        backoff_seconds = max(0, int(backoff_seconds))
        max_attempts = max(1, int(max_attempts))
    except (TypeError, ValueError):
        return blocked("retry_numeric_metadata_invalid")
    current_attempt = int(contract.get("attempt_number") or 1)
    if current_attempt >= max_attempts:
        return blocked("maximum_attempts_reached")
    earliest = _parse_time(earliest_retry_at)
    window_end = _parse_time(retry_window_ends_at)
    if earliest and window_end and earliest >= window_end:
        return blocked("retry_window_invalid")
    for item in current_retry_requests():
        if item.get("idempotency_key") == idempotency_key and item.get("request_state") in {"pending", "approved"}:
            return blocked("active_retry_idempotency_key_must_be_unique")
    job_binding = {
        "collection_job_id": collection_job_id,
        "collection_job_event_sha256": (contract.get("transition_history") or [contract])[-1].get("collection_job_event_sha256"),
        "current_state": contract.get("current_state"),
        "attempt_number": current_attempt,
        "failure_category": contract.get("failure_category"),
        "retry_eligible": contract.get("retry_eligible"),
    }
    retry_contract = {
        "idempotency_key": idempotency_key,
        "backoff_seconds": backoff_seconds,
        "earliest_retry_at": earliest.isoformat() if earliest else None,
        "retry_window_ends_at": window_end.isoformat() if window_end else None,
        "max_attempts": max_attempts,
        "requested_attempt_number": current_attempt + 1,
    }
    content = {
        "event_type": "retry_requested",
        "collection_job_id": collection_job_id,
        "job_binding": job_binding,
        "job_binding_sha256": _sha(job_binding),
        "retry_contract": retry_contract,
        "retry_contract_sha256": _sha(retry_contract),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        **retry_contract,
        "retry_request_id": f"retry-request-{digest[:24]}",
        "recovery_event_id": f"recovery-event-{digest[:24]}",
        "recovery_event_sha256": digest,
        "connector_execution_performed": False,
        "retry_execution_performed": False,
        "legacy_scan_job_mutated": False,
    }
    result = _record(ACTIONS[0], actor, collection_job_id, event, ip_address)
    return {**result, "status": "collection_retry_requested", "next_action": "review_retry_request"}


def decide_retry(*, actor: str, retry_request_id: str, approved: bool, decision_reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    request_record = find_retry_request(retry_request_id)
    if request_record is None:
        return blocked("retry_request_required")
    if request_record.get("request_state") != "pending":
        return blocked("pending_retry_request_required")
    if confirmed is not True:
        return blocked("explicit_retry_decision_confirmation_required")
    decision_reason = str(decision_reason or "").strip()
    if not decision_reason:
        return blocked("retry_decision_reason_required")
    request_binding = {
        "retry_request_id": retry_request_id,
        "recovery_event_sha256": request_record.get("recovery_event_sha256"),
        "collection_job_id": request_record.get("collection_job_id"),
        "requested_attempt_number": request_record.get("requested_attempt_number"),
    }
    content = {
        "event_type": "retry_decided",
        "retry_request_id": retry_request_id,
        "collection_job_id": request_record.get("collection_job_id"),
        "approved": approved is True,
        "request_binding": request_binding,
        "request_binding_sha256": _sha(request_binding),
        "decision_reason": decision_reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "recovery_event_id": f"recovery-event-{digest[:24]}",
        "recovery_event_sha256": digest,
        "retry_execution_performed": False,
        "connector_execution_performed": False,
    }
    result = _record(ACTIONS[1], actor, retry_request_id, event, ip_address)
    return {**result, "status": "collection_retry_decided", "next_action": "create_recovery_plan" if approved else "review_denied_retry"}


def create_recovery_plan(*, actor: str, collection_job_id: str, retry_request_id: str, plan_type: str, steps: Any, operator_required: bool, replacement_job_id: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    plan_type = str(plan_type or "").strip()
    if plan_type not in PLAN_TYPES:
        return blocked("recovery_plan_type_invalid")
    if confirmed is not True:
        return blocked("explicit_recovery_plan_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("recovery_plan_reason_required")
    retry_record = None
    if plan_type == "retry":
        retry_record = find_retry_request(retry_request_id)
        if retry_record is None or retry_record.get("request_state") != "approved":
            return blocked("approved_retry_request_required")
        if retry_record.get("collection_job_id") != collection_job_id:
            return blocked("retry_request_job_binding_mismatch")
    normalized_steps = [str(item).strip() for item in (steps or []) if str(item).strip()]
    if not normalized_steps:
        return blocked("recovery_plan_steps_required")
    plan = {
        "plan_type": plan_type,
        "steps": normalized_steps,
        "operator_required": bool(operator_required),
        "replacement_job_id": str(replacement_job_id or "").strip() or None,
        "retry_request_id": retry_request_id or None,
        "requested_attempt_number": retry_record.get("requested_attempt_number") if retry_record else None,
    }
    job_binding = {
        "collection_job_id": collection_job_id,
        "current_state": contract.get("current_state"),
        "attempt_number": contract.get("attempt_number"),
        "collection_job_event_sha256": (contract.get("transition_history") or [contract])[-1].get("collection_job_event_sha256"),
    }
    content = {
        "event_type": "recovery_plan_created",
        "collection_job_id": collection_job_id,
        "job_binding": job_binding,
        "job_binding_sha256": _sha(job_binding),
        "plan": plan,
        "plan_sha256": _sha(plan),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "recovery_plan_id": f"recovery-plan-{digest[:24]}",
        "recovery_event_id": f"recovery-event-{digest[:24]}",
        "recovery_event_sha256": digest,
        "retry_execution_performed": False,
        "connector_execution_performed": False,
        "legacy_scan_job_mutated": False,
    }
    result = _record(ACTIONS[2], actor, collection_job_id, event, ip_address)
    return {**result, "status": "collection_recovery_plan_created", "next_action": "operator_intervention_required" if operator_required else "dispatch_recovery_separately"}


def record_operator_intervention(*, actor: str, collection_job_id: str, intervention_type: str, resolution: str, replacement_job_id: str, apply_terminal_transition: bool, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    intervention_type = str(intervention_type or "").strip()
    if intervention_type not in INTERVENTION_TYPES:
        return blocked("operator_intervention_type_invalid")
    if confirmed is not True:
        return blocked("explicit_operator_intervention_confirmation_required")
    reason = str(reason or "").strip()
    resolution = str(resolution or "").strip()
    if not reason or not resolution:
        return blocked("operator_intervention_reason_and_resolution_required")
    replacement_job_id = str(replacement_job_id or "").strip()
    if intervention_type == "supersede" and not replacement_job_id:
        return blocked("replacement_job_id_required")
    transition_result = None
    if apply_terminal_transition and intervention_type in {"cancel", "supersede"}:
        transition_result = transition_collection_job(
            collection_job_id=collection_job_id,
            actor=actor,
            to_state="cancelled" if intervention_type == "cancel" else "superseded",
            authorization_binding=None,
            failure_category="",
            reason=reason,
            confirmed=True,
            ip_address=ip_address,
        )
        if transition_result.get("status") != "collection_job_transitioned":
            return blocked("operator_terminal_transition_invalid")
    intervention = {
        "intervention_type": intervention_type,
        "resolution": resolution,
        "replacement_job_id": replacement_job_id or None,
        "terminal_transition_applied": bool(transition_result),
        "transition_event_sha256": (transition_result or {}).get("collection_job_event_sha256"),
    }
    job_binding = {
        "collection_job_id": collection_job_id,
        "current_state_before_intervention": contract.get("current_state"),
        "attempt_number": contract.get("attempt_number"),
        "collection_job_event_sha256": (contract.get("transition_history") or [contract])[-1].get("collection_job_event_sha256"),
    }
    content = {
        "event_type": "operator_intervention_recorded",
        "collection_job_id": collection_job_id,
        "job_binding": job_binding,
        "job_binding_sha256": _sha(job_binding),
        "intervention": intervention,
        "intervention_sha256": _sha(intervention),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "operator_intervention_id": f"operator-intervention-{digest[:24]}",
        "recovery_event_id": f"recovery-event-{digest[:24]}",
        "recovery_event_sha256": digest,
        "retry_execution_performed": False,
        "connector_execution_performed": False,
        "legacy_scan_job_mutated": False,
        "evidence_mutated": False,
    }
    result = _record(ACTIONS[3], actor, collection_job_id, event, ip_address)
    next_action = "review_terminal_collection_state" if transition_result else "apply_resolution_through_controlled_workflow"
    return {**result, "status": "collection_operator_intervention_recorded", "next_action": next_action}
