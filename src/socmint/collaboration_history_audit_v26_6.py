from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from . import database
from .case_team_role_assignment_v26_1 import current_case_team
from .collaboration_requests_handoffs_v26_3 import build_workspace as build_requests_workspace
from .collaboration_responses_resolution_v26_4 import build_collaboration_response_workspace
from .collaboration_workspace_v26_0 import build_collaboration_workspace
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha
from .team_workload_collaboration_queue_v26_5 import build_team_workload_collaboration_queue

SCHEMA = "socmint.collaboration_history_audit.v26_6"
VERSION = "v26.6.0"

ACTION_TYPES = {
    "case_team_role_assignment": "team_assignment",
    "case_team_role_revocation": "role_revocation",
    "case_collaboration_note_created": "note_created",
    "case_collaboration_note_corrected": "note_corrected",
    "case_collaboration_mention_created": "mention_created",
    "case_collaboration_note_acknowledged": "note_acknowledged",
    "case_collaboration_update_read": "update_read",
    "case_collaboration_request_created": "request_created",
    "case_collaboration_request_acknowledged": "request_acknowledged",
    "case_collaboration_request_accepted": "request_accepted",
    "case_collaboration_request_declined": "request_declined",
    "case_collaboration_request_completed": "request_completed",
    "case_collaboration_request_cancelled": "request_cancelled",
    "case_collaboration_handoff_created": "handoff_created",
    "case_collaboration_handoff_acknowledged": "handoff_acknowledged",
    "case_collaboration_handoff_accepted": "handoff_accepted",
    "case_collaboration_handoff_declined": "handoff_declined",
    "case_collaboration_handoff_completed": "handoff_completed",
    "case_collaboration_handoff_cancelled": "handoff_cancelled",
    "case_collaboration_response_recorded": "response_recorded",
}


def _visible(case_id: str, allowed_case_ids: set[str] | None) -> bool:
    return allowed_case_ids is None or case_id in allowed_case_ids


def _affected_user(details: dict[str, Any]) -> str | None:
    for key in (
        "user_identity", "mentioned_user", "requested_from", "handoff_to",
        "responding_user", "acknowledged_by", "read_by_user",
    ):
        value = str(details.get(key) or "").strip()
        if value:
            return value
    return None


def _state_pair(action: str, details: dict[str, Any]) -> tuple[str | None, str | None]:
    if action == "case_team_role_assignment":
        previous = "active" if details.get("supersedes_assignment_id") else None
        return previous, str(details.get("assignment_status") or "active")
    if action == "case_team_role_revocation":
        return "active", "revoked"
    if action == "case_collaboration_note_corrected":
        return "active", "superseded"
    if action == "case_collaboration_note_created":
        return None, "active"
    if action == "case_collaboration_mention_created":
        return None, str(details.get("status") or "unread")
    if action == "case_collaboration_note_acknowledged":
        return "unacknowledged", "acknowledged"
    if action == "case_collaboration_update_read":
        return "unread", "read"
    if action == "case_collaboration_response_recorded":
        binding = details.get("previous_response_binding") or {}
        return binding.get("response_type"), details.get("response_type")
    binding = details.get("request_binding") or details.get("handoff_binding") or {}
    return binding.get("workflow_status"), details.get("workflow_status") or details.get("status")


def _persisted_events(allowed_case_ids: set[str] | None) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(tuple(ACTION_TYPES)))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        result = []
        for row in rows:
            case_id = str(row.target_value or "").strip()
            if not case_id or not _visible(case_id, allowed_case_ids):
                continue
            details = _json_details(row)
            previous_state, new_state = _state_pair(row.action, details)
            binding = {
                "record_id": row.id,
                "action": row.action,
                "target_value": row.target_value,
                "details": details,
            }
            result.append({
                "history_event_id": f"collaboration-audit-{row.id}",
                "event_type": ACTION_TYPES[row.action],
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "actor": row.actor,
                "affected_user": _affected_user(details),
                "case_id": case_id,
                "source_action": row.action,
                "source_record_id": row.id,
                "source_binding": binding,
                "source_binding_sha256": _sha(binding),
                "access_scope": details.get("workspace_access_scope") or {
                    "case_id": case_id,
                    "case_access_required": True,
                },
                "previous_state": previous_state,
                "new_state": new_state,
                "details": details,
                "synthetic_checkpoint": False,
            })
        return result
    finally:
        session.close()


def _checkpoint(now: str, queue: dict[str, Any]) -> dict[str, Any]:
    binding = {
        "schema": queue.get("schema"),
        "version": queue.get("version"),
        "status": queue.get("status"),
        "counts": queue.get("counts"),
        "queue_sha256": queue.get("queue_sha256"),
    }
    digest = _sha(binding)
    return {
        "history_event_id": f"collaboration-queue-checkpoint-{digest[:24]}",
        "event_type": "queue_checkpoint",
        "occurred_at": now,
        "actor": "system",
        "affected_user": queue.get("user_identity"),
        "case_id": None,
        "source_action": None,
        "source_record_id": None,
        "source_binding": binding,
        "source_binding_sha256": digest,
        "access_scope": queue.get("access_scope"),
        "previous_state": None,
        "new_state": queue.get("status"),
        "details": binding,
        "synthetic_checkpoint": True,
    }


def build_collaboration_history_audit(
    user_identity: str,
    *,
    allowed_case_ids: set[str] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current_time = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    generated_at = current_time.isoformat()
    user = str(user_identity or "").strip()

    workspace = build_collaboration_workspace(user, allowed_case_ids=allowed_case_ids)
    queue = build_team_workload_collaboration_queue(
        user,
        allowed_case_ids=allowed_case_ids,
        collaboration_workspace=workspace,
        now=current_time,
    )
    events = _persisted_events(allowed_case_ids)
    events.append(_checkpoint(generated_at, queue))
    events.sort(key=lambda item: (
        str(item.get("occurred_at") or ""),
        int(item.get("source_record_id") or 10**18),
        str(item.get("history_event_id") or ""),
    ))

    visible_case_ids = sorted({
        str(item.get("case_id"))
        for item in workspace.get("participating_cases") or []
        if item.get("case_id")
    })
    active_team = []
    current_owner = None
    open_requests = []
    pending_handoffs = []
    unresolved_responses = []
    for case_id in visible_case_ids:
        for assignment in current_case_team(case_id):
            if assignment.get("assignment_status") == "active":
                active_team.append({
                    "case_id": case_id,
                    "user_identity": assignment.get("user_identity"),
                    "role": assignment.get("role"),
                    "assignment_id": assignment.get("case_team_assignment_id"),
                })
                if assignment.get("role") == "case_owner":
                    current_owner = assignment.get("user_identity")
        request_state = build_requests_workspace(case_id)
        open_requests.extend(request_state.get("pending_requests") or [])
        pending_handoffs.extend(request_state.get("pending_handoffs") or [])
        response_state = build_collaboration_response_workspace(case_id)
        unresolved_responses.extend(response_state.get("unresolved_responses") or [])

    current_state = {
        "active_team": active_team,
        "current_owner": current_owner,
        "open_requests": open_requests,
        "pending_handoffs": pending_handoffs,
        "unacknowledged_items": queue.get("awaiting_acknowledgement") or [],
        "overdue_items": queue.get("overdue_items") or [],
        "unresolved_responses": unresolved_responses,
        "active_escalations": queue.get("supervisor_escalations") or [],
        "unresolved_actions": {
            "requests": len(open_requests),
            "handoffs": len(pending_handoffs),
            "unacknowledged": len(queue.get("awaiting_acknowledgement") or []),
            "overdue": len(queue.get("overdue_items") or []),
            "responses": len(unresolved_responses),
            "escalations": len(queue.get("supervisor_escalations") or []),
        },
    }
    event_counts = Counter(str(item.get("event_type")) for item in events)
    actor_counts = Counter(str(item.get("actor") or "unknown") for item in events)
    access_scope = {
        "mode": "restricted" if allowed_case_ids is not None else "all_visible_cases",
        "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if any(current_state["unresolved_actions"].values()) else "ready",
        "generated_at": generated_at,
        "user_identity": user,
        "access_scope": access_scope,
        "history": events,
        "event_count": len(events),
        "event_type_counts": dict(sorted(event_counts.items())),
        "actor_counts": dict(sorted(actor_counts.items())),
        "case_count": len(visible_case_ids),
        "source_bound_event_count": sum(1 for item in events if item.get("source_binding_sha256")),
        "current_collaboration_state": current_state,
        "current_collaboration_state_sha256": _sha(current_state),
        "source_records_mutated": False,
        "collaboration_events_mutated": False,
        "queue_record_created": False,
        "history_record_created": False,
        "case_access_scope_changed": False,
        "next_action": "review_collaboration_history_and_audit",
    }
