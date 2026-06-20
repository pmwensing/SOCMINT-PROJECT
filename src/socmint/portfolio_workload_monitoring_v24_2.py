from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from .persistent_decision_supervisor_queue_v19_3 import (
    OUTSTANDING_STATES,
    build_persistent_decision_supervisor_queue,
)

SCHEMA = "socmint.portfolio_workload_assignment_monitoring.v24_2"
VERSION = "v24.2.0"


def _parse(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    except (TypeError, ValueError):
        return None


def _assignment_age_hours(value: str | None, now: dt.datetime) -> float | None:
    assigned = _parse(value)
    if assigned is None:
        return None
    return max(
        0.0, round((now - assigned.astimezone(dt.UTC)).total_seconds() / 3600, 2)
    )


def build_workload_assignment_monitoring(
    *, now: dt.datetime | None = None
) -> dict[str, Any]:
    current_time = now or dt.datetime.now(dt.UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=dt.UTC)

    queue = build_persistent_decision_supervisor_queue(now=current_time)
    entries = list(queue.get("entries") or [])
    active_entries = [
        item for item in entries if item.get("review_state") in OUTSTANDING_STATES
    ]
    unassigned = [item for item in active_entries if not item.get("assigned_reviewer")]

    reviewer_entries: dict[str, list[dict[str, Any]]] = {}
    monitored_entries = []
    for item in entries:
        value = dict(item)
        value["assignment_age_hours"] = _assignment_age_hours(
            value.get("assigned_at"), current_time
        )
        reviewer = str(value.get("assigned_reviewer") or "").strip()
        if reviewer:
            reviewer_entries.setdefault(reviewer, []).append(value)
        monitored_entries.append(value)

    reviewers = []
    for reviewer, items in sorted(reviewer_entries.items()):
        active = [
            item for item in items if item.get("review_state") in OUTSTANDING_STATES
        ]
        counts = Counter(
            str(item.get("review_state") or "unreviewed") for item in items
        )
        ages = [
            float(item["assignment_age_hours"])
            for item in items
            if item.get("assignment_age_hours") is not None
        ]
        reviewers.append(
            {
                "reviewer": reviewer,
                "total_assigned": len(items),
                "active_workload": len(active),
                "unreviewed": counts.get("unreviewed", 0),
                "needs_follow_up": counts.get("needs_follow_up", 0),
                "reviewed": counts.get("reviewed", 0),
                "accepted": counts.get("accepted", 0),
                "oldest_assignment_age_hours": max(ages) if ages else None,
                "average_assignment_age_hours": round(sum(ages) / len(ages), 2)
                if ages
                else None,
                "reviewer_queue_href": "/case-intelligence-review/my-assignments",
                "supervisor_queue_href": f"/case-intelligence-review/supervisor-queue?assigned_reviewer={reviewer}",
            }
        )

    workloads = [item["active_workload"] for item in reviewers]
    min_workload = min(workloads) if workloads else 0
    max_workload = max(workloads) if workloads else 0
    spread = max_workload - min_workload
    average = round(sum(workloads) / len(workloads), 2) if workloads else 0.0
    overloaded_threshold = max(1, int(average + 1)) if reviewers else 0

    for reviewer in reviewers:
        reviewer["workload_delta_from_average"] = round(
            reviewer["active_workload"] - average, 2
        )
        reviewer["workload_imbalanced"] = (
            spread >= 2 and reviewer["active_workload"] == max_workload
        )
        reviewer["overloaded"] = (
            reviewer["active_workload"] >= overloaded_threshold
            and reviewer["active_workload"] > average
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if unassigned or spread >= 2 else "balanced",
        "generated_at": current_time.isoformat(),
        "counts": {
            "total_decisions": len(entries),
            "active_workload": len(active_entries),
            "assigned_active": len(active_entries) - len(unassigned),
            "unassigned_active": len(unassigned),
            "reviewer_count": len(reviewers),
        },
        "review_state_counts": queue.get("counts") or {},
        "reviewers": reviewers,
        "entries": monitored_entries,
        "unassigned_work": unassigned,
        "workload_balance": {
            "minimum_active_workload": min_workload,
            "maximum_active_workload": max_workload,
            "average_active_workload": average,
            "workload_spread": spread,
            "imbalanced": spread >= 2,
            "overloaded_threshold": overloaded_threshold,
        },
        "links": {
            "supervisor_queue": "/case-intelligence-review/supervisor-queue",
            "reviewer_queue": "/case-intelligence-review/my-assignments",
        },
        "source_assignments_mutated": False,
        "workload_record_created": False,
        "next_action": (
            "assign_unassigned_work"
            if unassigned
            else "rebalance_reviewer_workload"
            if spread >= 2
            else "monitor_reviewer_workload"
        ),
    }
