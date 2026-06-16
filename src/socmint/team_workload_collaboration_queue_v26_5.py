from __future__ import annotations

import datetime as dt
from collections import defaultdict
from statistics import mean
from typing import Any

from .case_team_role_assignment_v26_1 import current_case_team
from .collaboration_responses_resolution_v26_4 import build_collaboration_response_workspace
from .collaboration_workspace_v26_0 import _collaboration_events, build_collaboration_workspace
from .dossier_assembly_workspace_v21_0 import _sha
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.team_workload_collaboration_queue.v26_5"
VERSION = "v26.5.0"
TERMINAL_STATES = {"declined", "completed", "cancelled", "resolved", "resolution"}


def _parse(value: Any) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    except (TypeError, ValueError):
        return None


def _age_hours(value: Any, now: dt.datetime) -> float | None:
    parsed = _parse(value)
    if parsed is None:
        return None
    return round(max(0.0, (now - parsed.astimezone(dt.UTC)).total_seconds() / 3600), 2)


def _overdue(value: Any, now: dt.datetime) -> bool:
    parsed = _parse(value)
    return bool(parsed and parsed.astimezone(dt.UTC) < now)


def _links(case_id: str) -> dict[str, str]:
    return {
        "case": f"/case-intelligence-review/{case_id}",
        "team": f"/cases/{case_id}/team",
        "notes": f"/cases/{case_id}/collaboration-notes",
        "requests": f"/cases/{case_id}/collaboration-requests",
        "responses": f"/cases/{case_id}/collaboration-responses",
        "reviewer_queue": "/case-intelligence-review/queue",
        "supervisor_queue": "/case-intelligence-review/supervisor-queue",
    }


def build_team_workload_collaboration_queue(
    user_identity: str,
    *,
    allowed_case_ids: set[str] | None = None,
    collaboration_workspace: dict[str, Any] | None = None,
    workload: dict[str, Any] | None = None,
    team_by_case: dict[str, list[dict[str, Any]]] | None = None,
    response_by_case: dict[str, dict[str, Any]] | None = None,
    collaboration_events: list[dict[str, Any]] | None = None,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now_value = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    user = str(user_identity or "").strip()
    workspace = collaboration_workspace or build_collaboration_workspace(
        user,
        allowed_case_ids=allowed_case_ids,
    )
    workload_payload = workload or build_workload_assignment_monitoring()
    visible = None if allowed_case_ids is None else set(allowed_case_ids)

    participating_cases = list(workspace.get("participating_cases") or [])
    participating_ids = {str(item.get("case_id")) for item in participating_cases if item.get("case_id")}
    workload_entries = [
        item
        for item in workload_payload.get("entries") or []
        if item.get("case_id") and (visible is None or str(item.get("case_id")) in visible)
    ]
    case_ids = sorted(participating_ids | {str(item.get("case_id")) for item in workload_entries})

    teams = team_by_case or {case_id: current_case_team(case_id) for case_id in case_ids}
    responses = response_by_case or {
        case_id: build_collaboration_response_workspace(case_id) for case_id in case_ids
    }
    events = collaboration_events if collaboration_events is not None else _collaboration_events()
    events = [
        event
        for event in events
        if event.get("case_id") and (visible is None or str(event.get("case_id")) in visible)
    ]

    my_assigned_cases = [
        item
        for item in participating_cases
        if item.get("assigned_roles")
    ]
    pending_requests = list(workspace.get("pending_requests") or [])
    pending_handoffs = list(workspace.get("pending_handoffs") or [])
    unread_updates = list(workspace.get("unread_updates") or [])

    awaiting_acknowledgement = [
        item
        for item in pending_requests + pending_handoffs
        if str(item.get("status") or "") == "requested"
        or str(item.get("status") or "") == "pending"
    ]
    delegated_by_me = [
        item
        for item in pending_requests
        if str(item.get("requested_by") or "") == user
    ] + [
        item
        for item in pending_handoffs
        if str(item.get("handoff_from") or "") == user
    ]

    overdue_items = []
    for item in pending_requests + pending_handoffs:
        if _overdue(item.get("due_at"), now_value):
            overdue_items.append({
                **item,
                "overdue": True,
                "overdue_hours": _age_hours(item.get("due_at"), now_value),
                "links": item.get("links") or _links(str(item.get("case_id"))),
            })

    unassigned_work = []
    for item in workload_entries:
        reviewer = str(item.get("assigned_reviewer") or "").strip()
        if item.get("outstanding") and not reviewer:
            case_id = str(item.get("case_id"))
            unassigned_work.append({
                "case_id": case_id,
                "review_state": item.get("review_state"),
                "assignment_age_hours": item.get("assignment_age_hours"),
                "decision_record_id": item.get("decision_record_id"),
                "links": _links(case_id),
            })

    supervisor_escalations = []
    for case_id, payload in responses.items():
        for item in payload.get("unresolved_responses") or []:
            if item.get("response_type") == "escalation":
                supervisor_escalations.append({
                    **item,
                    "case_id": case_id,
                    "links": _links(case_id),
                })

    load_by_user: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"case_ids": set(), "roles": set(), "open_requests": 0, "open_handoffs": 0, "unread_updates": 0}
    )
    for case_id, assignments in teams.items():
        for assignment in assignments:
            if assignment.get("assignment_status") != "active":
                continue
            member = str(assignment.get("user_identity") or "").strip()
            if not member:
                continue
            load_by_user[member]["case_ids"].add(case_id)
            load_by_user[member]["roles"].add(str(assignment.get("role") or "participant"))
    for item in pending_requests:
        member = str(item.get("requested_from") or "").strip()
        if member:
            load_by_user[member]["open_requests"] += 1
    for item in pending_handoffs:
        member = str(item.get("handoff_to") or "").strip()
        if member:
            load_by_user[member]["open_handoffs"] += 1
    for item in unread_updates:
        member = user
        if member:
            load_by_user[member]["unread_updates"] += 1

    collaboration_load_by_user = []
    for member, load in sorted(load_by_user.items()):
        total = len(load["case_ids"]) + load["open_requests"] + load["open_handoffs"] + load["unread_updates"]
        collaboration_load_by_user.append({
            "user_identity": member,
            "active_case_count": len(load["case_ids"]),
            "case_ids": sorted(load["case_ids"]),
            "roles": sorted(load["roles"]),
            "open_requests": load["open_requests"],
            "open_handoffs": load["open_handoffs"],
            "unread_updates": load["unread_updates"],
            "total_collaboration_load": total,
        })

    load_values = [item["total_collaboration_load"] for item in collaboration_load_by_user]
    average_load = round(mean(load_values), 2) if load_values else 0.0
    workload_imbalance = [
        item
        for item in collaboration_load_by_user
        if average_load and item["total_collaboration_load"] > average_load * 1.5
    ]

    recent_activity = [
        {
            "case_id": event.get("case_id"),
            "action": event.get("action"),
            "actor": event.get("actor"),
            "occurred_at": event.get("occurred_at"),
            "age_hours": _age_hours(event.get("occurred_at"), now_value),
            "record_id": event.get("record_id"),
            "links": _links(str(event.get("case_id"))),
        }
        for event in sorted(events, key=lambda item: str(item.get("occurred_at") or ""), reverse=True)[:50]
    ]

    counts = {
        "my_assigned_cases": len(my_assigned_cases),
        "pending_requests": len(pending_requests),
        "awaiting_acknowledgement": len(awaiting_acknowledgement),
        "delegated_by_me": len(delegated_by_me),
        "pending_handoffs": len(pending_handoffs),
        "overdue_items": len(overdue_items),
        "unassigned_work": len(unassigned_work),
        "supervisor_escalations": len(supervisor_escalations),
        "recent_activity": len(recent_activity),
        "users_with_load": len(collaboration_load_by_user),
        "workload_imbalance": len(workload_imbalance),
    }
    core = {
        "user_identity": user,
        "my_assigned_cases": my_assigned_cases,
        "pending_requests": pending_requests,
        "awaiting_acknowledgement": awaiting_acknowledgement,
        "delegated_by_me": delegated_by_me,
        "pending_handoffs": pending_handoffs,
        "overdue_items": overdue_items,
        "unassigned_work": unassigned_work,
        "supervisor_escalations": supervisor_escalations,
        "recent_activity": recent_activity,
        "collaboration_load_by_user": collaboration_load_by_user,
        "workload_imbalance": workload_imbalance,
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if overdue_items or unassigned_work or supervisor_escalations else "ready",
        "generated_at": now_value.isoformat(),
        "access_scope": {
            "mode": "restricted" if allowed_case_ids is not None else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None,
        },
        **core,
        "counts": counts,
        "average_collaboration_load": average_load,
        "queue_sha256": _sha(core),
        "read_only": True,
        "source_records_mutated": False,
        "collaboration_record_created": False,
        "case_access_scope_changed": False,
        "next_action": "review_team_workload_and_collaboration_queue",
    }
