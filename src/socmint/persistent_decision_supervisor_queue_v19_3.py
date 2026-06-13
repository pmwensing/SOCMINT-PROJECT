from __future__ import annotations

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
VERSION = "v19.3.0"
OUTSTANDING_STATES = {"unreviewed", "needs_follow_up"}


def _age_hours(created_at: datetime | None, now: datetime) -> float | None:
    if created_at is None:
        return None
    value = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    return max(0.0, round((now - value.astimezone(UTC)).total_seconds() / 3600, 2))


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
        latest_annotations: dict[int, dict[str, Any]] = {}
        for row in annotations:
            details = _json_details(row)
            record_id = details.get("decision_record_id")
            if isinstance(record_id, int):
                latest_annotations[record_id] = {
                    "review_state": details.get("review_state") or "unreviewed",
                    "review_note": details.get("review_note") or "",
                    "assigned_reviewer": row.actor,
                    "reviewed_at": row.created_at.isoformat() if row.created_at else None,
                }

        entries: list[dict[str, Any]] = []
        state_counts: Counter[str] = Counter()
        case_counts: dict[str, Counter[str]] = defaultdict(Counter)
        reviewers: set[str] = set()
        oldest_outstanding_age_hours: float | None = None

        for row in decisions:
            details = _json_details(row)
            annotation = latest_annotations.get(row.id, {})
            state = str(annotation.get("review_state") or "unreviewed")
            assigned = annotation.get("assigned_reviewer")
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
                "outstanding": sum(counts.get(state, 0) for state in OUTSTANDING_STATES),
                "case_workspace_href": f"/case-intelligence-review/{current_case}",
            }
            for current_case, counts in sorted(case_counts.items())
        ]
        return {
            "schema": PERSISTENT_DECISION_SUPERVISOR_QUEUE_SCHEMA,
            "version": VERSION,
            "status": "available",
            "generated_at": current_time.isoformat(),
            "counts": {state: state_counts.get(state, 0) for state in sorted(REVIEW_STATES)},
            "total_decisions": sum(state_counts.values()),
            "total_outstanding": sum(state_counts.get(state, 0) for state in OUTSTANDING_STATES),
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
