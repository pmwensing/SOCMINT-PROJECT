from __future__ import annotations

from typing import Any

from . import database
from .collaboration_notes_workspace_v26_2 import find_note
from .collaboration_requests_handoffs_v26_3 import current_items
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard

SCHEMA = "socmint.collaboration_responses_resolution.v26_4"
VERSION = "v26.4.0"
ACTION = "case_collaboration_response_recorded"
RESPONSE_TYPES = (
    "acknowledgement",
    "acceptance",
    "decline",
    "response_note",
    "completion",
    "escalation",
    "resolution",
)
TARGET_TYPES = ("note", "request", "handoff")
TERMINAL_RESPONSES = {"decline", "completion", "resolution"}


def _blocked(case_id: str, key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "source_event_mutated": False,
        "case_access_scope_changed": False,
    }


def _case_state(case_id: str) -> dict[str, Any] | None:
    payload = build_portfolio_operations_dashboard()
    item = next(
        (
            row
            for row in payload.get("cases") or []
            if str(row.get("case_id") or "") == case_id
        ),
        None,
    )
    return (
        None
        if item is None
        else {
            "portfolio_schema": payload.get("schema"),
            "portfolio_version": payload.get("version"),
            "case": item,
        }
    )


def response_history(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(
                database.AuditLog.target_value == case_id,
                database.AuditLog.action == ACTION,
            )
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "action_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "source_action": row.action,
            }
            for row in rows
        ]
    finally:
        session.close()


def _source_item(
    case_id: str, target_type: str, target_id: str
) -> dict[str, Any] | None:
    if target_type == "note":
        return find_note(case_id, target_id)
    items = current_items(case_id)
    key = "requests" if target_type == "request" else "handoffs"
    id_key = f"collaboration_{target_type}_id"
    return next((item for item in items[key] if item.get(id_key) == target_id), None)


def _source_binding(target_type: str, item: dict[str, Any]) -> dict[str, Any]:
    if target_type == "note":
        return {
            "target_type": target_type,
            "target_id": item.get("collaboration_note_id"),
            "target_sha256": item.get("collaboration_note_sha256"),
            "action_record_id": item.get("action_record_id"),
            "current_state": item.get("note_status"),
            "author": item.get("author"),
        }
    return {
        "target_type": target_type,
        "target_id": item.get(f"collaboration_{target_type}_id"),
        "target_sha256": item.get(f"collaboration_{target_type}_sha256"),
        "action_record_id": item.get("action_record_id"),
        "current_state": item.get("workflow_status") or item.get("status"),
        "requested_by": item.get("requested_by") or item.get("handoff_from"),
        "requested_from": item.get("requested_from") or item.get("handoff_to"),
    }


def latest_response_state(
    case_id: str, target_type: str, target_id: str
) -> dict[str, Any] | None:
    matches = [
        event
        for event in response_history(case_id)
        if event.get("target_type") == target_type
        and event.get("target_id") == target_id
    ]
    return matches[-1] if matches else None


def record_collaboration_response(
    case_id: str,
    *,
    target_type: str,
    target_id: str,
    response_type: str,
    responding_user: str,
    reason: str,
    confirmed: bool,
    unresolved_reason: str | None = None,
    resolution_code: str | None = None,
    allowed_case_ids: set[str] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids:
        return _blocked(case_id, "case_access_required")
    if confirmed is not True:
        return _blocked(
            case_id, "explicit_collaboration_response_confirmation_required"
        )
    if target_type not in TARGET_TYPES:
        return _blocked(case_id, "collaboration_response_target_not_in_catalog")
    if response_type not in RESPONSE_TYPES:
        return _blocked(case_id, "collaboration_response_type_not_in_catalog")
    target_id = str(target_id or "").strip()
    if not target_id:
        return _blocked(case_id, "collaboration_response_target_id_required")
    reason = str(reason or "").strip()
    if not reason:
        return _blocked(case_id, "collaboration_response_reason_required")

    item = _source_item(case_id, target_type, target_id)
    if item is None:
        return _blocked(case_id, "collaboration_response_source_required")
    if target_type == "note" and item.get("note_status") != "active":
        return _blocked(case_id, "active_collaboration_note_required")

    previous = latest_response_state(case_id, target_type, target_id)
    if previous and previous.get("response_type") in TERMINAL_RESPONSES:
        return _blocked(case_id, "open_collaboration_response_required")

    case_state = _case_state(case_id)
    if case_state is None:
        return _blocked(case_id, "source_case_state_required")

    binding = _source_binding(target_type, item)
    previous_binding = None
    if previous:
        previous_binding = {
            "collaboration_response_id": previous.get("collaboration_response_id"),
            "collaboration_response_sha256": previous.get(
                "collaboration_response_sha256"
            ),
            "response_type": previous.get("response_type"),
            "action_record_id": previous.get("action_record_id"),
        }

    core = {
        "case_id": case_id,
        "target_type": target_type,
        "target_id": target_id,
        "response_type": response_type,
        "responding_user": str(responding_user or "unknown"),
        "reason": reason,
        "unresolved_reason": str(unresolved_reason or "").strip() or None,
        "resolution_code": str(resolution_code or "").strip() or None,
        "source_binding": binding,
        "source_binding_sha256": _sha(binding),
        "previous_response_binding": previous_binding,
        "previous_response_binding_sha256": _sha(previous_binding)
        if previous_binding
        else None,
        "source_case_state": case_state,
        "source_case_state_sha256": _sha(case_state),
    }
    digest = _sha(core)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "collaboration_response_id": f"collaboration-response-{digest[:24]}",
        "collaboration_response_sha256": digest,
        "collaboration_event_id": f"collaboration-event-{digest[:24]}",
        "collaboration_event_sha256": digest,
        "source_records_mutated": False,
        "source_event_mutated": False,
        "prior_response_mutated": False,
        "case_access_scope_changed": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=str(responding_user or "unknown"),
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        recorded_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "collaboration_response_recorded",
        "action_record_id": record_id,
        "recorded_by": str(responding_user or "unknown"),
        "recorded_at": recorded_at,
        "next_action": "review_collaboration_responses",
    }


def build_collaboration_response_workspace(case_id: str) -> dict[str, Any]:
    events = response_history(case_id)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for event in events:
        key = (str(event.get("target_type") or ""), str(event.get("target_id") or ""))
        if all(key):
            latest[key] = event
    unresolved = [
        event
        for event in latest.values()
        if event.get("response_type") not in TERMINAL_RESPONSES
    ]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if unresolved else "ready",
        "case_id": case_id,
        "response_types": list(RESPONSE_TYPES),
        "target_types": list(TARGET_TYPES),
        "latest_responses": sorted(
            latest.values(), key=lambda item: str(item.get("recorded_at") or "")
        ),
        "unresolved_responses": unresolved,
        "counts": {
            "history": len(events),
            "targets": len(latest),
            "unresolved": len(unresolved),
            "resolved": len(latest) - len(unresolved),
        },
        "history": events,
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_collaboration_responses",
    }
