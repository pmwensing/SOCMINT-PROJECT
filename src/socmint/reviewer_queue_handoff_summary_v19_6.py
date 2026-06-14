from __future__ import annotations

from collections import defaultdict
from typing import Any

from .persistent_decision_supervisor_queue_v19_3 import (
    build_persistent_decision_supervisor_queue,
)

REVIEWER_QUEUE_HANDOFF_SUMMARY_SCHEMA = (
    "socmint.reviewer_queue_handoff_summary.v19_6"
)
VERSION = "v19.6.0"
COMPLETED_STATES = {"reviewed", "accepted"}
OUTSTANDING_STATES = {"unreviewed"}
FOLLOW_UP_STATES = {"needs_follow_up"}


def build_reviewer_queue_handoff_summary(
    *,
    reviewer: str | None = None,
    case_id: str | None = None,
) -> dict[str, Any]:
    queue = build_persistent_decision_supervisor_queue(
        assigned_reviewer=reviewer,
        case_id=case_id,
    )
    entries = list(queue.get("entries") or [])

    reviewer_rollup: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "assigned": 0,
            "completed": 0,
            "outstanding": 0,
            "follow_up": 0,
            "accepted": 0,
            "reviewed": 0,
            "oldest_open_age_hours": None,
        }
    )
    case_rollup: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "completed": 0,
            "outstanding": 0,
            "follow_up": 0,
            "reviewers": set(),
            "oldest_open_age_hours": None,
        }
    )

    completed_items = []
    outstanding_items = []
    follow_up_items = []

    for item in entries:
        state = str(item.get("review_state") or "unreviewed")
        assigned = str(item.get("assigned_reviewer") or "unassigned")
        current_case = str(item.get("case_id") or "unknown")
        age = item.get("age_hours")

        reviewer_row = reviewer_rollup[assigned]
        reviewer_row["reviewer"] = assigned
        reviewer_row["assigned"] += 1
        case_row = case_rollup[current_case]
        case_row["case_id"] = current_case
        case_row["total"] += 1
        case_row["reviewers"].add(assigned)

        if state in COMPLETED_STATES:
            completed_items.append(item)
            reviewer_row["completed"] += 1
            reviewer_row[state] += 1
            case_row["completed"] += 1
        elif state in FOLLOW_UP_STATES:
            follow_up_items.append(item)
            reviewer_row["follow_up"] += 1
            case_row["follow_up"] += 1
        else:
            outstanding_items.append(item)
            reviewer_row["outstanding"] += 1
            case_row["outstanding"] += 1

        if state not in COMPLETED_STATES and age is not None:
            reviewer_oldest = reviewer_row["oldest_open_age_hours"]
            case_oldest = case_row["oldest_open_age_hours"]
            reviewer_row["oldest_open_age_hours"] = max(
                float(reviewer_oldest or 0), float(age)
            )
            case_row["oldest_open_age_hours"] = max(
                float(case_oldest or 0), float(age)
            )

    reviewer_summaries = []
    for row in reviewer_rollup.values():
        assigned = int(row["assigned"])
        completed = int(row["completed"])
        row["completion_rate"] = (
            round((completed / assigned) * 100, 2) if assigned else 0.0
        )
        row["handoff_ready"] = (
            row["outstanding"] == 0
            and row["follow_up"] == 0
            and completed > 0
        )
        reviewer_summaries.append(row)
    reviewer_summaries.sort(key=lambda row: row["reviewer"])

    case_summaries = []
    for row in case_rollup.values():
        row["reviewers"] = sorted(row["reviewers"])
        row["handoff_ready"] = (
            row["outstanding"] == 0
            and row["follow_up"] == 0
            and row["completed"] == row["total"]
            and row["total"] > 0
        )
        row["case_workspace_href"] = (
            f"/case-intelligence-review/{row['case_id']}"
        )
        case_summaries.append(row)
    case_summaries.sort(key=lambda row: row["case_id"])

    handoff_ready = (
        bool(entries)
        and not outstanding_items
        and not follow_up_items
        and len(completed_items) == len(entries)
    )
    return {
        "schema": REVIEWER_QUEUE_HANDOFF_SUMMARY_SCHEMA,
        "version": VERSION,
        "status": "ready_for_handoff" if handoff_ready else "review_in_progress",
        "handoff_ready": handoff_ready,
        "entry_count": len(entries),
        "completed_count": len(completed_items),
        "outstanding_count": len(outstanding_items),
        "follow_up_count": len(follow_up_items),
        "completed_items": completed_items,
        "outstanding_items": outstanding_items,
        "follow_up_items": follow_up_items,
        "reviewer_summaries": reviewer_summaries,
        "case_summaries": case_summaries,
        "filters": {"reviewer": reviewer, "case_id": case_id},
        "next_action": (
            "prepare_supervisor_handoff"
            if handoff_ready
            else "complete_reviewer_queue"
        ),
    }
