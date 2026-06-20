from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .portfolio_blocked_overdue_queue_v24_3 import build_blocked_overdue_case_queue

SCHEMA = "socmint.portfolio_supervisor_escalation.v24_4"
VERSION = "v24.4.0"

ACTIONS = {
    "escalate": "portfolio_case_escalated",
    "acknowledge": "portfolio_case_escalation_acknowledged",
    "reassign": "portfolio_case_escalation_reassigned",
    "resolve": "portfolio_case_escalation_resolved",
}


def _queue_item(case_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    snapshot = build_blocked_overdue_case_queue()
    item = next(
        (
            value
            for value in snapshot.get("queue") or []
            if value.get("case_id") == case_id
        ),
        None,
    )
    return item, snapshot


def _latest(case_id: str, action: str | None = None) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        query = session.query(database.AuditLog).filter(
            database.AuditLog.target_value == case_id,
            database.AuditLog.action.in_(tuple(ACTIONS.values())),
        )
        if action:
            query = query.filter(database.AuditLog.action == action)
        row = query.order_by(
            database.AuditLog.created_at.desc(), database.AuditLog.id.desc()
        ).first()
        if row is None:
            return None
        return {
            **_json_details(row),
            "action_record_id": row.id,
            "recorded_by": row.actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def latest_escalation(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, ACTIONS["escalate"])


def escalation_history(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(
                database.AuditLog.target_value == case_id,
                database.AuditLog.action.in_(tuple(ACTIONS.values())),
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
            }
            for row in rows
        ]
    finally:
        session.close()


def _blocked(case_id: str, key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
    }


def _record(
    case_id: str,
    *,
    control: str,
    actor: str,
    note: str,
    payload: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    item, snapshot = _queue_item(case_id)
    if item is None:
        return _blocked(case_id, "blocked_or_overdue_queue_item_required")

    source_state = {
        "case_id": case_id,
        "queue_schema": snapshot.get("schema"),
        "queue_version": snapshot.get("version"),
        "queue_thresholds": snapshot.get("thresholds"),
        "queue_item": item,
    }
    content = {
        "case_id": case_id,
        "control": control,
        "note": str(note or "").strip(),
        "payload": payload,
        "source_state": source_state,
        "source_state_sha256": _sha(source_state),
    }
    event_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "control_event_id": f"portfolio-{control}-{event_sha256[:24]}",
        "control_event_sha256": event_sha256,
        "source_records_mutated": False,
        "case_events_mutated": False,
        "stage_events_mutated": False,
        "assignment_events_mutated": False,
        "queue_snapshot_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTIONS[control],
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
        "status": f"{control}_recorded",
        "action_record_id": record_id,
        "recorded_by": actor,
        "recorded_at": recorded_at,
    }


def record_escalation(
    case_id: str,
    *,
    confirmed: bool,
    supervisor: str,
    reason: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return _blocked(case_id, "explicit_escalation_confirmation_required")
    reason_value = str(reason or "").strip()
    if not reason_value:
        return _blocked(case_id, "escalation_reason_required")
    return _record(
        case_id,
        control="escalate",
        actor=supervisor,
        note=note,
        payload={"reason": reason_value},
        ip_address=ip_address,
    )


def acknowledge_escalation(
    case_id: str,
    *,
    confirmed: bool,
    supervisor: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return _blocked(case_id, "explicit_escalation_acknowledgement_required")
    escalation = latest_escalation(case_id)
    if escalation is None:
        return _blocked(case_id, "escalation_required")
    return _record(
        case_id,
        control="acknowledge",
        actor=supervisor,
        note=note,
        payload={
            "escalation_event_id": escalation.get("control_event_id"),
            "escalation_event_sha256": escalation.get("control_event_sha256"),
            "escalation_record_id": escalation.get("action_record_id"),
        },
        ip_address=ip_address,
    )


def reassign_escalation(
    case_id: str,
    *,
    confirmed: bool,
    supervisor: str,
    assigned_reviewer: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return _blocked(case_id, "explicit_escalation_reassignment_required")
    reviewer = str(assigned_reviewer or "").strip()
    if not reviewer:
        return _blocked(case_id, "assigned_reviewer_required")
    escalation = latest_escalation(case_id)
    if escalation is None:
        return _blocked(case_id, "escalation_required")
    return _record(
        case_id,
        control="reassign",
        actor=supervisor,
        note=note,
        payload={
            "assigned_reviewer": reviewer,
            "escalation_event_id": escalation.get("control_event_id"),
            "escalation_event_sha256": escalation.get("control_event_sha256"),
        },
        ip_address=ip_address,
    )


def resolve_escalation(
    case_id: str,
    *,
    confirmed: bool,
    supervisor: str,
    resolution: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return _blocked(case_id, "explicit_escalation_resolution_required")
    resolution_value = str(resolution or "").strip()
    if not resolution_value:
        return _blocked(case_id, "escalation_resolution_required")
    escalation = latest_escalation(case_id)
    if escalation is None:
        return _blocked(case_id, "escalation_required")
    return _record(
        case_id,
        control="resolve",
        actor=supervisor,
        note=note,
        payload={
            "resolution": resolution_value,
            "escalation_event_id": escalation.get("control_event_id"),
            "escalation_event_sha256": escalation.get("control_event_sha256"),
        },
        ip_address=ip_address,
    )


def build_escalation_control_state() -> dict[str, Any]:
    queue = build_blocked_overdue_case_queue()
    items = []
    for item in queue.get("queue") or []:
        case_id = str(item.get("case_id"))
        history = escalation_history(case_id)
        latest = history[-1] if history else None
        items.append(
            {
                **item,
                "latest_control": latest,
                "control_history_count": len(history),
                "escalated": any(
                    value.get("control") == "escalate" for value in history
                ),
                "acknowledged": any(
                    value.get("control") == "acknowledge" for value in history
                ),
                "resolved": bool(latest and latest.get("control") == "resolve"),
            }
        )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if items else "clear",
        "items": items,
        "item_count": len(items),
        "source_records_mutated": False,
        "next_action": "review_supervisor_escalations"
        if items
        else "monitor_portfolio",
    }
