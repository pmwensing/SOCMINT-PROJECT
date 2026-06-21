from __future__ import annotations

from typing import Any

from .persistent_case_review_decisions_v19_0 import (
    set_persistent_decision_review_state,
)
from .persistent_decision_supervisor_queue_v19_3 import (
    build_persistent_decision_supervisor_queue,
)

REVIEWER_WORK_QUEUE_SCHEMA = "socmint.reviewer_work_queue.v19_5"
VERSION = "v19.5.0"
REVIEWER_STATES = {"reviewed", "needs_follow_up", "accepted"}


def build_reviewer_work_queue(reviewer: str) -> dict[str, Any]:
    queue = build_persistent_decision_supervisor_queue(
        assigned_reviewer=reviewer,
    )
    entries = list(queue.get("entries") or [])
    return {
        "schema": REVIEWER_WORK_QUEUE_SCHEMA,
        "version": VERSION,
        "status": "available",
        "reviewer": reviewer,
        "entry_count": len(entries),
        "entries": entries,
        "oldest_assignment_age_hours": max(
            [float(item.get("age_hours") or 0) for item in entries],
            default=None,
        ),
        "counts": {
            "unreviewed": sum(
                1 for item in entries if item.get("review_state") == "unreviewed"
            ),
            "needs_follow_up": sum(
                1 for item in entries if item.get("review_state") == "needs_follow_up"
            ),
            "reviewed": sum(
                1 for item in entries if item.get("review_state") == "reviewed"
            ),
            "accepted": sum(
                1 for item in entries if item.get("review_state") == "accepted"
            ),
        },
        "allowed_review_states": sorted(REVIEWER_STATES),
        "next_action": ("review_assigned_decisions" if entries else "await_assignment"),
    }


def update_assigned_decision_review_state(
    case_id: str,
    decision_record_id: int,
    review_state: str,
    *,
    reviewer: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    state = str(review_state or "").strip()
    if state not in REVIEWER_STATES:
        return {
            "status": "blocked",
            "blockers": [
                {"key": "unsupported_reviewer_state", "detail": state or "missing"}
            ],
            "next_action": "choose_supported_review_state",
        }

    queue = build_persistent_decision_supervisor_queue(
        case_id=case_id,
        assigned_reviewer=reviewer,
    )
    matching = [
        item
        for item in queue.get("entries") or []
        if int(item.get("decision_record_id") or 0) == int(decision_record_id)
    ]
    if not matching:
        return {
            "status": "blocked",
            "blockers": [
                {
                    "key": "decision_not_assigned_to_reviewer",
                    "detail": str(decision_record_id),
                }
            ],
            "next_action": "refresh_reviewer_work_queue",
        }

    result = set_persistent_decision_review_state(
        case_id,
        decision_record_id,
        state,
        actor=reviewer,
        note=note,
        ip_address=ip_address,
    )
    result["reviewer_work_queue"] = build_reviewer_work_queue(reviewer)
    result["original_decision_mutated"] = False
    return result
