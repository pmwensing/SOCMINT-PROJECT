from __future__ import annotations

import datetime as dt
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard

SCHEMA = "socmint.case_team_role_assignment.v26_1"
VERSION = "v26.1.0"
ASSIGN_ACTION = "case_team_role_assignment"
REVOKE_ACTION = "case_team_role_revocation"
ACTIONS = (ASSIGN_ACTION, REVOKE_ACTION)

ROLE_CATALOG = (
    "case_owner",
    "lead_analyst",
    "analyst",
    "reviewer",
    "supervisor",
    "evidence_custodian",
    "observer",
)


def _blocked(case_id: str, key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "case_access_scope_changed": False,
    }


def _case_state(case_id: str) -> dict[str, Any] | None:
    portfolio = build_portfolio_operations_dashboard()
    item = next(
        (
            value
            for value in portfolio.get("cases") or []
            if str(value.get("case_id") or "") == case_id
        ),
        None,
    )
    if item is None:
        return None
    return {
        "portfolio_schema": portfolio.get("schema"),
        "portfolio_version": portfolio.get("version"),
        "case": item,
    }


def case_team_history(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(
                database.AuditLog.target_value == case_id,
                database.AuditLog.action.in_(ACTIONS),
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


def current_case_team(case_id: str) -> list[dict[str, Any]]:
    assignments: dict[str, dict[str, Any]] = {}
    for event in case_team_history(case_id):
        assignment_id = str(event.get("case_team_assignment_id") or "")
        if not assignment_id:
            continue
        if event.get("event_type") == "assignment":
            superseded = str(event.get("supersedes_assignment_id") or "")
            if superseded in assignments:
                assignments[superseded] = {
                    **assignments[superseded],
                    "assignment_status": "superseded",
                    "superseded_by_assignment_id": assignment_id,
                }
            assignments[assignment_id] = {
                **event,
                "assignment_status": "active",
            }
        elif event.get("event_type") == "revocation" and assignment_id in assignments:
            assignments[assignment_id] = {
                **assignments[assignment_id],
                "assignment_status": "revoked",
                "revocation_event_id": event.get("case_team_event_id"),
                "revoked_by": event.get("recorded_by"),
                "revoked_at": event.get("recorded_at"),
                "revocation_reason": event.get("reason"),
            }
    return sorted(
        assignments.values(),
        key=lambda item: (
            str(item.get("user_identity") or ""),
            str(item.get("role") or ""),
            str(item.get("recorded_at") or ""),
        ),
    )


def latest_active_assignment(
    case_id: str,
    *,
    user_identity: str,
    role: str,
) -> dict[str, Any] | None:
    user_value = str(user_identity or "").strip()
    role_value = str(role or "").strip()
    matches = [
        item
        for item in current_case_team(case_id)
        if item.get("assignment_status") == "active"
        and item.get("user_identity") == user_value
        and item.get("role") == role_value
    ]
    return matches[-1] if matches else None


def assign_case_team_role(
    case_id: str,
    *,
    user_identity: str,
    role: str,
    assigned_by: str,
    reason: str,
    confirmed: bool,
    effective_from: str | None = None,
    effective_until: str | None = None,
    allowed_case_ids: set[str] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids:
        return _blocked(case_id, "case_access_required")
    if confirmed is not True:
        return _blocked(case_id, "explicit_case_team_assignment_confirmation_required")

    user_value = str(user_identity or "").strip()
    if not user_value:
        return _blocked(case_id, "team_member_identity_required")
    role_value = str(role or "").strip()
    if role_value not in ROLE_CATALOG:
        return _blocked(case_id, "case_team_role_not_in_catalog")
    reason_value = str(reason or "").strip()
    if not reason_value:
        return _blocked(case_id, "case_team_assignment_reason_required")

    source_case_state = _case_state(case_id)
    if source_case_state is None:
        return _blocked(case_id, "source_case_state_required")

    previous = latest_active_assignment(
        case_id,
        user_identity=user_value,
        role=role_value,
    )
    effective_from_value = str(effective_from or "").strip() or None
    effective_until_value = str(effective_until or "").strip() or None
    content = {
        "case_id": case_id,
        "event_type": "assignment",
        "user_identity": user_value,
        "role": role_value,
        "assigned_by": str(assigned_by or "unknown"),
        "reason": reason_value,
        "effective_from": effective_from_value,
        "effective_until": effective_until_value,
        "assignment_status": "active",
        "supersedes_assignment_id": (
            previous.get("case_team_assignment_id") if previous else None
        ),
        "supersedes_assignment_sha256": (
            previous.get("case_team_event_sha256") if previous else None
        ),
        "source_case_state": source_case_state,
        "source_case_state_sha256": _sha(source_case_state),
    }
    event_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "case_team_assignment_id": f"case-team-assignment-{event_sha256[:24]}",
        "case_team_event_id": f"case-team-event-{event_sha256[:24]}",
        "case_team_event_sha256": event_sha256,
        "source_records_mutated": False,
        "prior_assignments_mutated": False,
        "case_access_scope_changed": False,
        "access_granted_by_assignment": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=str(assigned_by or "unknown"),
            action=ASSIGN_ACTION,
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
        "status": "case_team_assignment_recorded",
        "action_record_id": record_id,
        "recorded_by": str(assigned_by or "unknown"),
        "recorded_at": recorded_at,
        "next_action": "review_case_team",
    }


def revoke_case_team_role(
    case_id: str,
    assignment_id: str,
    *,
    revoked_by: str,
    reason: str,
    confirmed: bool,
    allowed_case_ids: set[str] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if allowed_case_ids is not None and case_id not in allowed_case_ids:
        return _blocked(case_id, "case_access_required")
    if confirmed is not True:
        return _blocked(case_id, "explicit_case_team_revocation_confirmation_required")
    reason_value = str(reason or "").strip()
    if not reason_value:
        return _blocked(case_id, "case_team_revocation_reason_required")

    assignment = next(
        (
            item
            for item in current_case_team(case_id)
            if item.get("case_team_assignment_id") == assignment_id
        ),
        None,
    )
    if assignment is None:
        return _blocked(case_id, "case_team_assignment_required")
    if assignment.get("assignment_status") != "active":
        return _blocked(case_id, "active_case_team_assignment_required")

    source_case_state = _case_state(case_id)
    if source_case_state is None:
        return _blocked(case_id, "source_case_state_required")

    assignment_binding = {
        "case_team_assignment_id": assignment.get("case_team_assignment_id"),
        "case_team_event_id": assignment.get("case_team_event_id"),
        "case_team_event_sha256": assignment.get("case_team_event_sha256"),
        "action_record_id": assignment.get("action_record_id"),
        "user_identity": assignment.get("user_identity"),
        "role": assignment.get("role"),
    }
    content = {
        "case_id": case_id,
        "event_type": "revocation",
        "case_team_assignment_id": assignment_id,
        "user_identity": assignment.get("user_identity"),
        "role": assignment.get("role"),
        "revoked_by": str(revoked_by or "unknown"),
        "reason": reason_value,
        "assignment_status": "revoked",
        "assignment_binding": assignment_binding,
        "assignment_binding_sha256": _sha(assignment_binding),
        "source_case_state": source_case_state,
        "source_case_state_sha256": _sha(source_case_state),
    }
    event_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "case_team_event_id": f"case-team-revocation-{event_sha256[:24]}",
        "case_team_event_sha256": event_sha256,
        "source_records_mutated": False,
        "assignment_event_mutated": False,
        "case_access_scope_changed": False,
        "access_revoked_by_role_event": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=str(revoked_by or "unknown"),
            action=REVOKE_ACTION,
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
        "status": "case_team_revocation_recorded",
        "action_record_id": record_id,
        "recorded_by": str(revoked_by or "unknown"),
        "recorded_at": recorded_at,
        "next_action": "review_case_team",
    }


def build_case_team_workspace(case_id: str) -> dict[str, Any]:
    history = case_team_history(case_id)
    assignments = current_case_team(case_id)
    active = [item for item in assignments if item.get("assignment_status") == "active"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "case_id": case_id,
        "role_catalog": list(ROLE_CATALOG),
        "current_assignments": assignments,
        "active_assignments": active,
        "active_assignment_count": len(active),
        "history": history,
        "history_count": len(history),
        "source_records_mutated": False,
        "read_only_view_created_record": False,
        "case_access_scope_changed": False,
        "next_action": "manage_case_team_roles",
    }
