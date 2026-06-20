from __future__ import annotations

from typing import Any
from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard

SCHEMA = "socmint.collaboration_requests_handoffs.v26_3"
VERSION = "v26.3.0"
REQUEST_TYPES = (
    "evidence_review",
    "correlation_review",
    "closure_review",
    "archive_verification",
    "supervisor_decision",
    "task_review",
)
HANDOFF_TYPES = ("case_ownership", "evidence_custody", "review_task", "unresolved_task")
PRIORITIES = ("low", "normal", "high", "urgent")
REQUEST_ACTIONS = {
    "requested": "case_collaboration_request_created",
    "acknowledged": "case_collaboration_request_acknowledged",
    "accepted": "case_collaboration_request_accepted",
    "declined": "case_collaboration_request_declined",
    "completed": "case_collaboration_request_completed",
    "cancelled": "case_collaboration_request_cancelled",
}
HANDOFF_ACTIONS = {
    "pending": "case_collaboration_handoff_created",
    "acknowledged": "case_collaboration_handoff_acknowledged",
    "accepted": "case_collaboration_handoff_accepted",
    "declined": "case_collaboration_handoff_declined",
    "completed": "case_collaboration_handoff_completed",
    "cancelled": "case_collaboration_handoff_cancelled",
}
ALL_ACTIONS = tuple(REQUEST_ACTIONS.values()) + tuple(HANDOFF_ACTIONS.values())
TERMINAL = {"declined", "completed", "cancelled"}


def _blocked(case_id, key):
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "case_access_scope_changed": False,
    }


def _case_state(case_id):
    p = build_portfolio_operations_dashboard()
    item = next(
        (x for x in p.get("cases") or [] if str(x.get("case_id") or "") == case_id),
        None,
    )
    return (
        None
        if item is None
        else {
            "portfolio_schema": p.get("schema"),
            "portfolio_version": p.get("version"),
            "case": item,
        }
    )


def _record(case_id, actor, action, event, ip):
    _ensure_storage()
    s = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=case_id,
            ip_address=ip,
            details=_canonical(event),
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return row.id, row.created_at.isoformat() if row.created_at else None
    finally:
        s.close()


def history(case_id):
    _ensure_storage()
    s = database.Session()
    try:
        rows = (
            s.query(database.AuditLog)
            .filter(
                database.AuditLog.target_value == case_id,
                database.AuditLog.action.in_(ALL_ACTIONS),
            )
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(r),
                "action_record_id": r.id,
                "recorded_by": r.actor,
                "recorded_at": r.created_at.isoformat() if r.created_at else None,
                "source_action": r.action,
            }
            for r in rows
        ]
    finally:
        s.close()


def current_items(case_id):
    requests = {}
    handoffs = {}
    for e in history(case_id):
        rid = str(e.get("collaboration_request_id") or "")
        hid = str(e.get("collaboration_handoff_id") or "")
        if rid:
            requests[rid] = {**requests.get(rid, {}), **e}
        if hid:
            handoffs[hid] = {**handoffs.get(hid, {}), **e}
    return {
        "requests": sorted(
            requests.values(), key=lambda x: str(x.get("recorded_at") or "")
        ),
        "handoffs": sorted(
            handoffs.values(), key=lambda x: str(x.get("recorded_at") or "")
        ),
    }


def _create(
    kind,
    case_id,
    *,
    actor,
    other,
    item_type,
    reason,
    priority,
    due_at,
    source_records,
    confirmed,
    allowed_case_ids,
    ip_address,
):
    if allowed_case_ids is not None and case_id not in allowed_case_ids:
        return _blocked(case_id, "case_access_required")
    if confirmed is not True:
        return _blocked(case_id, f"explicit_collaboration_{kind}_confirmation_required")
    if not str(other or "").strip():
        return _blocked(case_id, f"collaboration_{kind}_counterparty_required")
    if not str(reason or "").strip():
        return _blocked(case_id, f"collaboration_{kind}_reason_required")
    catalog = REQUEST_TYPES if kind == "request" else HANDOFF_TYPES
    if item_type not in catalog:
        return _blocked(case_id, f"collaboration_{kind}_type_not_in_catalog")
    if priority not in PRIORITIES:
        return _blocked(case_id, f"collaboration_{kind}_priority_not_in_catalog")
    state = _case_state(case_id)
    if state is None:
        return _blocked(case_id, "source_case_state_required")
    refs = [dict(x) for x in (source_records or []) if isinstance(x, dict)]
    status = "requested" if kind == "request" else "pending"
    core = {
        "case_id": case_id,
        "event_type": kind,
        "status": status,
        "reason": str(reason).strip(),
        "priority": priority,
        "due_at": str(due_at or "").strip() or None,
        "source_records": refs,
        "source_records_sha256": _sha(refs),
        "source_case_state": state,
        "source_case_state_sha256": _sha(state),
    }
    if kind == "request":
        core |= {
            "request_type": item_type,
            "requested_by": actor,
            "requested_from": str(other).strip(),
        }
    else:
        core |= {
            "handoff_type": item_type,
            "handoff_from": actor,
            "handoff_to": str(other).strip(),
        }
    digest = _sha(core)
    ident = f"collaboration-{kind}-{digest[:24]}"
    core[f"collaboration_{kind}_id"] = ident
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        f"collaboration_{kind}_sha256": digest,
        "collaboration_event_id": f"collaboration-event-{digest[:24]}",
        "collaboration_event_sha256": digest,
        "source_records_mutated": False,
        "prior_events_mutated": False,
        "case_access_scope_changed": False,
    }
    rec, at = _record(
        case_id,
        actor,
        (REQUEST_ACTIONS if kind == "request" else HANDOFF_ACTIONS)[status],
        event,
        ip_address,
    )
    return {
        **event,
        "status": f"collaboration_{kind}_recorded",
        "workflow_status": status,
        "action_record_id": rec,
        "recorded_by": actor,
        "recorded_at": at,
        "next_action": f"review_collaboration_{kind}s",
    }


def create_request(case_id, **kwargs):
    return _create("request", case_id, **kwargs)


def create_handoff(case_id, **kwargs):
    return _create("handoff", case_id, **kwargs)


def transition(
    kind,
    case_id,
    item_id,
    *,
    actor,
    decision,
    reason,
    confirmed,
    allowed_case_ids=None,
    ip_address=None,
):
    if allowed_case_ids is not None and case_id not in allowed_case_ids:
        return _blocked(case_id, "case_access_required")
    if confirmed is not True:
        return _blocked(
            case_id, f"explicit_collaboration_{kind}_transition_confirmation_required"
        )
    actions = REQUEST_ACTIONS if kind == "request" else HANDOFF_ACTIONS
    if decision not in actions or decision in {"requested", "pending"}:
        return _blocked(case_id, f"collaboration_{kind}_transition_not_in_catalog")
    items = current_items(case_id)[kind + "s"]
    item = next(
        (x for x in items if x.get(f"collaboration_{kind}_id") == item_id), None
    )
    if item is None:
        return _blocked(case_id, f"collaboration_{kind}_required")
    current = str(item.get("workflow_status") or item.get("status") or "")
    if current in TERMINAL:
        return _blocked(case_id, f"open_collaboration_{kind}_required")
    binding = {
        f"collaboration_{kind}_id": item_id,
        f"collaboration_{kind}_sha256": item.get(f"collaboration_{kind}_sha256"),
        "action_record_id": item.get("action_record_id"),
        "workflow_status": current,
    }
    core = {
        "case_id": case_id,
        "event_type": kind,
        f"collaboration_{kind}_id": item_id,
        "workflow_status": decision,
        "status": decision,
        "transitioned_by": actor,
        "reason": str(reason or "").strip() or None,
        f"{kind}_binding": binding,
        f"{kind}_binding_sha256": _sha(binding),
    }
    digest = _sha(core)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **core,
        "collaboration_event_id": f"collaboration-{kind}-{decision}-{digest[:24]}",
        "collaboration_event_sha256": digest,
        "source_records_mutated": False,
        "source_event_mutated": False,
        "case_access_scope_changed": False,
    }
    rec, at = _record(case_id, actor, actions[decision], event, ip_address)
    return {
        **event,
        "status": f"collaboration_{kind}_{decision}",
        "action_record_id": rec,
        "recorded_by": actor,
        "recorded_at": at,
        "next_action": f"review_collaboration_{kind}s",
    }


def build_workspace(case_id):
    items = current_items(case_id)
    req = items["requests"]
    hand = items["handoffs"]
    open_req = [
        x
        for x in req
        if str(x.get("workflow_status") or x.get("status")) not in TERMINAL
    ]
    open_hand = [
        x
        for x in hand
        if str(x.get("workflow_status") or x.get("status")) not in TERMINAL
    ]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if open_req or open_hand else "ready",
        "case_id": case_id,
        "request_types": list(REQUEST_TYPES),
        "handoff_types": list(HANDOFF_TYPES),
        "priorities": list(PRIORITIES),
        "requests": req,
        "handoffs": hand,
        "pending_requests": open_req,
        "pending_handoffs": open_hand,
        "counts": {
            "requests": len(req),
            "handoffs": len(hand),
            "pending_requests": len(open_req),
            "pending_handoffs": len(open_hand),
        },
        "history": history(case_id),
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_review_requests_and_handoffs",
    }
