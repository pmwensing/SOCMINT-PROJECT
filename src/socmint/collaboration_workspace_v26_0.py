from __future__ import annotations

from collections import defaultdict
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.collaboration_workspace.v26_0"
VERSION = "v26.0.0"

TEAM_ACTIONS = {"case_team_role_assignment", "case_team_role_revocation"}
REQUEST_ACTIONS = {
    "case_collaboration_request_created",
    "case_collaboration_request_acknowledged",
    "case_collaboration_request_accepted",
    "case_collaboration_request_declined",
    "case_collaboration_request_completed",
    "case_collaboration_request_cancelled",
}
HANDOFF_ACTIONS = {
    "case_collaboration_handoff_created",
    "case_collaboration_handoff_acknowledged",
    "case_collaboration_handoff_accepted",
    "case_collaboration_handoff_declined",
    "case_collaboration_handoff_completed",
    "case_collaboration_handoff_cancelled",
}
UPDATE_ACTIONS = {
    "case_collaboration_note_created",
    "case_collaboration_mention_created",
    "case_collaboration_update_created",
    "case_collaboration_update_read",
}
OPEN_STATES = {"requested", "pending", "acknowledged", "accepted", "overdue"}


def _collaboration_events() -> list[dict[str, Any]]:
    _ensure_storage()
    actions = tuple(
        sorted(TEAM_ACTIONS | REQUEST_ACTIONS | HANDOFF_ACTIONS | UPDATE_ACTIONS)
    )
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(actions))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                "record_id": row.id,
                "action": row.action,
                "case_id": str(row.target_value or "").strip(),
                "actor": row.actor,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            }
            for row in rows
            if str(row.target_value or "").strip()
        ]
    finally:
        session.close()


def _visible(case_id: str, allowed_case_ids: set[str] | None) -> bool:
    return allowed_case_ids is None or case_id in allowed_case_ids


def _latest_by_key(
    events: list[dict[str, Any]],
    *,
    actions: set[str],
    key_names: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("action") not in actions:
            continue
        details = event.get("details") or {}
        key = next(
            (
                str(details.get(name) or "").strip()
                for name in key_names
                if details.get(name)
            ),
            "",
        )
        if key:
            latest[key] = event
    return latest


def _case_links(case_id: str) -> dict[str, str]:
    return {
        "case": f"/case-intelligence-review/{case_id}",
        "evidence": f"/dossier-assembly/{case_id}",
        "review": f"/case-intelligence-review/{case_id}",
        "closure": f"/case-closure/{case_id}",
        "archive": f"/case-closure/{case_id}/history",
        "release": f"/dossier-release/{case_id}",
        "cross_case": "/cross-case-intelligence",
        "relationship_graph": "/cross-case-intelligence/graph",
    }


def build_collaboration_workspace(
    user_identity: str,
    *,
    allowed_case_ids: set[str] | None = None,
    portfolio: dict[str, Any] | None = None,
    workload: dict[str, Any] | None = None,
    collaboration_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    user = str(user_identity or "").strip()
    portfolio_payload = portfolio or build_portfolio_operations_dashboard()
    workload_payload = workload or build_workload_assignment_monitoring()
    events = (
        collaboration_events
        if collaboration_events is not None
        else _collaboration_events()
    )
    events = [
        event
        for event in events
        if event.get("case_id") and _visible(str(event["case_id"]), allowed_case_ids)
    ]

    portfolio_cases = {
        str(item.get("case_id")): item
        for item in portfolio_payload.get("cases") or []
        if item.get("case_id") and _visible(str(item.get("case_id")), allowed_case_ids)
    }
    workload_entries = [
        item
        for item in workload_payload.get("entries") or []
        if item.get("case_id") and _visible(str(item.get("case_id")), allowed_case_ids)
    ]

    roles_by_case: dict[str, set[str]] = defaultdict(set)
    collaborators_by_case: dict[str, set[str]] = defaultdict(set)
    participation_reasons: dict[str, set[str]] = defaultdict(set)

    for item in workload_entries:
        case_id = str(item.get("case_id"))
        reviewer = str(item.get("assigned_reviewer") or "").strip()
        assigned_by = str(item.get("assigned_by") or "").strip()
        actor = str(item.get("actor") or "").strip()
        for collaborator in (reviewer, assigned_by, actor):
            if collaborator:
                collaborators_by_case[case_id].add(collaborator)
        if reviewer == user:
            roles_by_case[case_id].add("reviewer")
            participation_reasons[case_id].add("assigned_review_work")
        if assigned_by == user:
            roles_by_case[case_id].add("supervisor")
            participation_reasons[case_id].add("assigned_review_work_to_others")
        if actor == user:
            roles_by_case[case_id].add("analyst")
            participation_reasons[case_id].add("case_decision_activity")

    latest_team = _latest_by_key(
        events,
        actions=TEAM_ACTIONS,
        key_names=("case_team_assignment_id", "assignment_id"),
    )
    for event in latest_team.values():
        details = event.get("details") or {}
        case_id = str(event.get("case_id"))
        member = str(
            details.get("user_identity") or details.get("member") or ""
        ).strip()
        role = str(details.get("role") or "participant").strip()
        status = str(
            details.get("assignment_status") or details.get("status") or "active"
        ).lower()
        if member and status not in {"revoked", "inactive", "expired"}:
            collaborators_by_case[case_id].add(member)
            if member == user:
                roles_by_case[case_id].add(role)
                participation_reasons[case_id].add("case_team_assignment")

    for event in events:
        case_id = str(event.get("case_id"))
        details = event.get("details") or {}
        actor = str(event.get("actor") or "").strip()
        requested_by = str(details.get("requested_by") or "").strip()
        requested_from = str(details.get("requested_from") or "").strip()
        assigned_to = str(
            details.get("assigned_to") or details.get("handoff_to") or ""
        ).strip()
        mentioned = {
            str(value).strip()
            for value in details.get("mentioned_users") or []
            if str(value).strip()
        }
        for collaborator in {
            actor,
            requested_by,
            requested_from,
            assigned_to,
        } | mentioned:
            if collaborator:
                collaborators_by_case[case_id].add(collaborator)
        if (
            user in {actor, requested_by, requested_from, assigned_to}
            or user in mentioned
        ):
            roles_by_case[case_id].add("participant")
            participation_reasons[case_id].add("collaboration_event")

    available_case_ids = (
        set(portfolio_cases)
        | {str(item.get("case_id")) for item in workload_entries}
        | {str(event.get("case_id")) for event in events}
    )
    participating_case_ids = sorted(set(roles_by_case) & available_case_ids)

    latest_requests = _latest_by_key(
        events,
        actions=REQUEST_ACTIONS,
        key_names=("collaboration_request_id", "request_id"),
    )
    pending_requests = []
    for request_id, event in latest_requests.items():
        details = event.get("details") or {}
        status = str(
            details.get("status") or details.get("request_status") or "requested"
        ).lower()
        requested_from = str(details.get("requested_from") or "").strip()
        requested_by = str(
            details.get("requested_by") or event.get("actor") or ""
        ).strip()
        if status in OPEN_STATES and user in {requested_from, requested_by}:
            pending_requests.append(
                {
                    "collaboration_request_id": request_id,
                    "case_id": event.get("case_id"),
                    "request_type": details.get("request_type"),
                    "status": status,
                    "priority": details.get("priority"),
                    "requested_by": requested_by,
                    "requested_from": requested_from,
                    "due_at": details.get("due_at"),
                    "source_record_id": event.get("record_id"),
                    "source_action": event.get("action"),
                    "links": _case_links(str(event.get("case_id"))),
                }
            )

    latest_handoffs = _latest_by_key(
        events,
        actions=HANDOFF_ACTIONS,
        key_names=("collaboration_handoff_id", "handoff_id"),
    )
    pending_handoffs = []
    for handoff_id, event in latest_handoffs.items():
        details = event.get("details") or {}
        status = str(
            details.get("status") or details.get("handoff_status") or "pending"
        ).lower()
        from_user = str(
            details.get("handoff_from")
            or details.get("requested_by")
            or event.get("actor")
            or ""
        ).strip()
        to_user = str(
            details.get("handoff_to") or details.get("assigned_to") or ""
        ).strip()
        if status in OPEN_STATES and user in {from_user, to_user}:
            pending_handoffs.append(
                {
                    "collaboration_handoff_id": handoff_id,
                    "case_id": event.get("case_id"),
                    "handoff_type": details.get("handoff_type"),
                    "status": status,
                    "handoff_from": from_user,
                    "handoff_to": to_user,
                    "due_at": details.get("due_at"),
                    "source_record_id": event.get("record_id"),
                    "source_action": event.get("action"),
                    "links": _case_links(str(event.get("case_id"))),
                }
            )

    unread_updates = []
    latest_updates = _latest_by_key(
        events,
        actions=UPDATE_ACTIONS,
        key_names=("collaboration_update_id", "mention_id", "note_id"),
    )
    for update_id, event in latest_updates.items():
        details = event.get("details") or {}
        mentioned = {
            str(value).strip()
            for value in details.get("mentioned_users") or []
            if str(value).strip()
        }
        recipients = {
            str(value).strip()
            for value in details.get("recipients") or []
            if str(value).strip()
        }
        read_by = {
            str(value).strip()
            for value in details.get("read_by") or []
            if str(value).strip()
        }
        status = str(details.get("status") or "unread").lower()
        if user in mentioned | recipients and user not in read_by and status != "read":
            unread_updates.append(
                {
                    "collaboration_update_id": update_id,
                    "case_id": event.get("case_id"),
                    "update_type": details.get("update_type") or event.get("action"),
                    "author": event.get("actor"),
                    "priority": details.get("priority"),
                    "occurred_at": event.get("occurred_at"),
                    "source_record_id": event.get("record_id"),
                    "links": _case_links(str(event.get("case_id"))),
                }
            )

    unresolved_review_requests = [
        {
            "case_id": item.get("case_id"),
            "decision_record_id": item.get("decision_record_id"),
            "review_state": item.get("review_state"),
            "assigned_reviewer": item.get("assigned_reviewer"),
            "assignment_age_hours": item.get("assignment_age_hours"),
            "case_workspace_href": item.get("case_workspace_href"),
        }
        for item in workload_entries
        if item.get("outstanding")
        and user
        in {
            str(item.get("assigned_reviewer") or "").strip(),
            str(item.get("assigned_by") or "").strip(),
            str(item.get("actor") or "").strip(),
        }
    ]

    participating_cases = []
    for case_id in participating_case_ids:
        item = portfolio_cases.get(case_id, {"case_id": case_id})
        blockers = list(item.get("blockers") or [])
        participating_cases.append(
            {
                "case_id": case_id,
                "assigned_roles": sorted(roles_by_case[case_id]),
                "participation_reasons": sorted(participation_reasons[case_id]),
                "stage": item.get("stage"),
                "status": item.get("status"),
                "blocked": bool(item.get("blocked")),
                "blockers": blockers,
                "active_collaborators": sorted(collaborators_by_case[case_id] - {user}),
                "latest_activity_at": item.get("latest_activity_at"),
                "links": _case_links(case_id),
            }
        )

    active_collaborators = [
        {
            "user_identity": collaborator,
            "case_ids": sorted(
                case_id
                for case_id in participating_case_ids
                if collaborator in collaborators_by_case[case_id]
            ),
            "shared_case_count": sum(
                1
                for case_id in participating_case_ids
                if collaborator in collaborators_by_case[case_id]
            ),
        }
        for collaborator in sorted(
            {
                value
                for case_id in participating_case_ids
                for value in collaborators_by_case[case_id]
                if value and value != user
            }
        )
    ]

    blocked_items = [
        {
            "case_id": item["case_id"],
            "blockers": item["blockers"],
            "assigned_roles": item["assigned_roles"],
            "links": item["links"],
        }
        for item in participating_cases
        if item["blocked"]
    ]
    blocked_items.extend(
        {
            "case_id": item.get("case_id"),
            "blockers": [
                {
                    "key": "outstanding_review_request",
                    "review_state": item.get("review_state"),
                }
            ],
            "assigned_roles": sorted(roles_by_case[str(item.get("case_id"))]),
            "links": _case_links(str(item.get("case_id"))),
        }
        for item in unresolved_review_requests
        if item.get("review_state") == "needs_follow_up"
    )

    unresolved_actions = []
    unresolved_actions.extend(
        {
            "key": "respond_to_collaboration_request",
            "case_id": item["case_id"],
            "record_id": item["source_record_id"],
        }
        for item in pending_requests
    )
    unresolved_actions.extend(
        {
            "key": "complete_or_decline_handoff",
            "case_id": item["case_id"],
            "record_id": item["source_record_id"],
        }
        for item in pending_handoffs
    )
    unresolved_actions.extend(
        {
            "key": "review_unread_update",
            "case_id": item["case_id"],
            "record_id": item["source_record_id"],
        }
        for item in unread_updates
    )
    unresolved_actions.extend(
        {
            "key": "resolve_review_request",
            "case_id": item["case_id"],
            "record_id": item["decision_record_id"],
        }
        for item in unresolved_review_requests
    )
    unresolved_actions.extend(
        {"key": "resolve_collaboration_blocker", "case_id": item["case_id"]}
        for item in blocked_items
    )

    counts = {
        "participating_cases": len(participating_cases),
        "active_collaborators": len(active_collaborators),
        "pending_requests": len(pending_requests),
        "pending_handoffs": len(pending_handoffs),
        "unread_updates": len(unread_updates),
        "unresolved_review_requests": len(unresolved_review_requests),
        "blocked_collaboration_items": len(blocked_items),
        "unresolved_collaboration_actions": len(unresolved_actions),
    }
    core = {
        "user_identity": user,
        "participating_cases": participating_cases,
        "active_collaborators": active_collaborators,
        "pending_requests": pending_requests,
        "pending_handoffs": pending_handoffs,
        "unread_updates": unread_updates,
        "unresolved_review_requests": unresolved_review_requests,
        "blocked_collaboration_items": blocked_items,
        "unresolved_collaboration_actions": unresolved_actions,
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if unresolved_actions else "ready",
        "user_identity": user,
        "access_scope": {
            "mode": "restricted"
            if allowed_case_ids is not None
            else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids)
            if allowed_case_ids is not None
            else None,
        },
        **core,
        "counts": counts,
        "workspace_sha256": _sha(core),
        "read_only": True,
        "source_records_mutated": False,
        "collaboration_record_created": False,
        "access_granted_by_mention": False,
        "next_action": "review_collaboration_workspace",
    }
