from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from . import database
from .persistent_case_review_decisions_v19_0 import (
    AUDIT_ACTION,
    REVIEW_ACTION,
    REVIEW_STATES,
    _ensure_audit_storage,
    _json_details,
)

PERSISTENT_DECISION_SUPERVISOR_QUEUE_SCHEMA = (
    "socmint.persistent_decision_supervisor_queue.v19_3"
)
VERSION = "v19.4.0"
OUTSTANDING_STATES = {"unreviewed", "needs_follow_up"}
ASSIGNMENT_ACTION = "case_intelligence_review_decision_assignment"


def _age_hours(created_at: datetime | None, now: datetime) -> float | None:
    if created_at is None:
        return None
    value = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    return max(0.0, round((now - value.astimezone(UTC)).total_seconds() / 3600, 2))


def assign_persistent_decision_reviewer(
    case_id: str,
    decision_record_id: int,
    reviewer: str,
    *,
    actor: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    assigned_reviewer = str(reviewer or "").strip()
    if not assigned_reviewer:
        return {
            "status": "blocked",
            "blockers": [{"key": "assigned_reviewer_required", "detail": "missing"}],
            "next_action": "choose_assigned_reviewer",
        }

    _ensure_audit_storage()
    session = database.Session()
    try:
        source = (
            session.query(database.AuditLog)
            .filter_by(
                id=int(decision_record_id),
                action=AUDIT_ACTION,
                target_value=case_id,
            )
            .one_or_none()
        )
        if source is None:
            return {
                "status": "blocked",
                "blockers": [
                    {
                        "key": "decision_record_not_found",
                        "detail": str(decision_record_id),
                    }
                ],
                "next_action": "refresh_supervisor_queue",
            }

        latest_review = (
            session.query(database.AuditLog)
            .filter_by(action=REVIEW_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .all()
        )
        review_state = "unreviewed"
        for row in latest_review:
            details = _json_details(row)
            if details.get("decision_record_id") == source.id:
                review_state = str(details.get("review_state") or "unreviewed")
                break
        if review_state not in OUTSTANDING_STATES:
            return {
                "status": "blocked",
                "blockers": [
                    {
                        "key": "decision_not_outstanding",
                        "detail": review_state,
                    }
                ],
                "next_action": "review_supervisor_queue",
            }

        assignment = database.AuditLog(
            actor=actor,
            action=ASSIGNMENT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=json.dumps(
                {
                    "case_id": case_id,
                    "decision_record_id": source.id,
                    "assigned_reviewer": assigned_reviewer,
                    "assignment_note": str(note or "").strip(),
                },
                sort_keys=True,
            ),
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return {
            "status": "recorded",
            "case_id": case_id,
            "decision_record_id": source.id,
            "assigned_reviewer": assigned_reviewer,
            "assigned_by": actor,
            "assignment_note": str(note or "").strip(),
            "assigned_at": assignment.created_at.isoformat()
            if assignment.created_at
            else None,
            "assignment_record_id": assignment.id,
            "original_decision_mutated": False,
            "next_action": "refresh_supervisor_queue",
        }
    finally:
        session.close()


def build_persistent_decision_supervisor_queue(
    *,
    case_id: str | None = None,
    review_state: str | None = None,
    assigned_reviewer: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    _ensure_audit_storage()
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    session = database.Session()
    try:
        decisions = (
            session.query(database.AuditLog)
            .filter_by(action=AUDIT_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        annotations = (
            session.query(database.AuditLog)
            .filter_by(action=REVIEW_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        assignments = (
            session.query(database.AuditLog)
            .filter_by(action=ASSIGNMENT_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        latest_annotations: dict[int, dict[str, Any]] = {}
        for row in annotations:
            details = _json_details(row)
            record_id = details.get("decision_record_id")
            if isinstance(record_id, int):
                latest_annotations[record_id] = {
                    "review_state": details.get("review_state") or "unreviewed",
                    "review_note": details.get("review_note") or "",
                    "legacy_reviewer": row.actor,
                    "reviewed_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                }
        latest_assignments: dict[int, dict[str, Any]] = {}
        for row in assignments:
            details = _json_details(row)
            record_id = details.get("decision_record_id")
            if isinstance(record_id, int):
                latest_assignments[record_id] = {
                    "assigned_reviewer": details.get("assigned_reviewer"),
                    "assignment_note": details.get("assignment_note") or "",
                    "assigned_by": row.actor,
                    "assigned_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "assignment_record_id": row.id,
                }

        entries: list[dict[str, Any]] = []
        state_counts: Counter[str] = Counter()
        case_counts: dict[str, Counter[str]] = defaultdict(Counter)
        reviewers: set[str] = set()
        oldest_outstanding_age_hours: float | None = None

        for row in decisions:
            details = _json_details(row)
            annotation = latest_annotations.get(row.id, {})
            assignment = latest_assignments.get(row.id, {})
            state = str(annotation.get("review_state") or "unreviewed")
            assigned = assignment.get("assigned_reviewer") or annotation.get(
                "legacy_reviewer"
            )
            age_hours = _age_hours(row.created_at, current_time)
            entry = {
                "decision_record_id": row.id,
                "case_id": row.target_value,
                "actor": row.actor,
                "decision": details.get("decision"),
                "note": details.get("note"),
                "persisted_at": row.created_at.isoformat() if row.created_at else None,
                "review_state": state,
                "assigned_reviewer": assigned,
                "assigned_by": assignment.get("assigned_by"),
                "assigned_at": assignment.get("assigned_at"),
                "assignment_note": assignment.get("assignment_note") or "",
                "assignment_record_id": assignment.get("assignment_record_id"),
                "review_note": annotation.get("review_note") or "",
                "reviewed_at": annotation.get("reviewed_at"),
                "age_hours": age_hours,
                "outstanding": state in OUTSTANDING_STATES,
                "case_workspace_href": f"/case-intelligence-review/{row.target_value}",
            }
            state_counts[state] += 1
            case_counts[str(row.target_value)][state] += 1
            if assigned:
                reviewers.add(str(assigned))
            if entry["outstanding"] and age_hours is not None:
                oldest_outstanding_age_hours = max(
                    oldest_outstanding_age_hours or 0.0, age_hours
                )
            if case_id and entry["case_id"] != case_id:
                continue
            if review_state and state != review_state:
                continue
            if assigned_reviewer and assigned != assigned_reviewer:
                continue
            entries.append(entry)

        entries.sort(
            key=lambda item: (
                not item["outstanding"],
                -(item["age_hours"] or 0),
                item["case_id"],
                item["decision_record_id"],
            )
        )
        case_summaries = [
            {
                "case_id": current_case,
                "total": sum(counts.values()),
                "unreviewed": counts.get("unreviewed", 0),
                "needs_follow_up": counts.get("needs_follow_up", 0),
                "reviewed": counts.get("reviewed", 0),
                "accepted": counts.get("accepted", 0),
                "outstanding": sum(
                    counts.get(state, 0) for state in OUTSTANDING_STATES
                ),
                "case_workspace_href": f"/case-intelligence-review/{current_case}",
            }
            for current_case, counts in sorted(case_counts.items())
        ]
        return {
            "schema": PERSISTENT_DECISION_SUPERVISOR_QUEUE_SCHEMA,
            "version": VERSION,
            "status": "available",
            "generated_at": current_time.isoformat(),
            "counts": {
                state: state_counts.get(state, 0) for state in sorted(REVIEW_STATES)
            },
            "total_decisions": sum(state_counts.values()),
            "total_outstanding": sum(
                state_counts.get(state, 0) for state in OUTSTANDING_STATES
            ),
            "oldest_outstanding_age_hours": oldest_outstanding_age_hours,
            "assigned_reviewers": sorted(reviewers),
            "case_summaries": case_summaries,
            "entries": entries,
            "entry_count": len(entries),
            "filters": {
                "case_id": case_id,
                "review_state": review_state,
                "assigned_reviewer": assigned_reviewer,
            },
            "review_states": sorted(REVIEW_STATES),
            "next_action": "review_outstanding_persistent_decisions",
        }
    finally:
        session.close()
