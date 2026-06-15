from __future__ import annotations

import os
from typing import Any

from .portfolio_case_stage_overview_v24_1 import build_case_status_stage_overview
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.portfolio_blocked_overdue_queue.v24_3"
VERSION = "v24.3.0"


def _threshold(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _severity(
    *, blocked: bool, stage_age: float | None, assignment_age: float | None,
    stage_limit: float, assignment_limit: float,
) -> tuple[str, int]:
    stage_overdue = stage_age is not None and stage_age > stage_limit
    assignment_overdue = assignment_age is not None and assignment_age > assignment_limit
    extreme = (
        (stage_age is not None and stage_age > stage_limit * 2)
        or (assignment_age is not None and assignment_age > assignment_limit * 2)
    )
    if blocked and (extreme or (stage_overdue and assignment_overdue)):
        return "critical", 4
    if blocked or (stage_overdue and assignment_overdue):
        return "high", 3
    if stage_overdue or assignment_overdue:
        return "medium", 2
    return "low", 1


def build_blocked_overdue_case_queue() -> dict[str, Any]:
    stage_limit = _threshold("SOCMINT_STAGE_OVERDUE_HOURS", 72.0)
    assignment_limit = _threshold("SOCMINT_ASSIGNMENT_OVERDUE_HOURS", 48.0)
    portfolio = build_portfolio_operations_dashboard()
    stage_overview = build_case_status_stage_overview()
    workload = build_workload_assignment_monitoring()

    portfolio_cases = {item["case_id"]: item for item in portfolio.get("cases") or []}
    stage_cases = {item["case_id"]: item for item in stage_overview.get("cases") or []}
    active_assignments: dict[str, list[dict[str, Any]]] = {}
    for item in workload.get("entries") or []:
        if item.get("review_state") not in {"unreviewed", "needs_follow_up"}:
            continue
        active_assignments.setdefault(str(item.get("case_id")), []).append(item)

    queue = []
    case_ids = sorted(set(portfolio_cases) | set(stage_cases) | set(active_assignments))
    for case_id in case_ids:
        portfolio_case = portfolio_cases.get(case_id, {})
        stage_case = stage_cases.get(case_id, {})
        assignments = active_assignments.get(case_id, [])
        assignment_ages = [
            float(item["assignment_age_hours"])
            for item in assignments
            if item.get("assignment_age_hours") is not None
        ]
        assignment_age = max(assignment_ages) if assignment_ages else None
        stage_age = stage_case.get("stage_duration_hours")
        stage_age = float(stage_age) if stage_age is not None else None
        blocked = bool(stage_case.get("blocked") or portfolio_case.get("blocked"))
        stage_overdue = stage_age is not None and stage_age > stage_limit
        assignment_overdue = assignment_age is not None and assignment_age > assignment_limit
        if not (blocked or stage_overdue or assignment_overdue):
            continue

        severity, severity_rank = _severity(
            blocked=blocked,
            stage_age=stage_age,
            assignment_age=assignment_age,
            stage_limit=stage_limit,
            assignment_limit=assignment_limit,
        )
        reviewers = sorted({
            str(item.get("assigned_reviewer"))
            for item in assignments
            if item.get("assigned_reviewer")
        })
        blockers = stage_case.get("blockers") or portfolio_case.get("blockers") or []
        blocking_reason = stage_case.get("blocking_reason") or (
            blockers[0].get("key") if blockers else None
        )
        links = portfolio_case.get("links") or {
            "case_review": f"/case-intelligence-review/{case_id}",
            "dossier_assembly": f"/dossier-assembly/{case_id}",
            "closure_workspace": f"/case-closure/{case_id}",
            "closure_history": f"/case-closure/{case_id}/history",
        }
        queue.append({
            "case_id": case_id,
            "severity": severity,
            "severity_rank": severity_rank,
            "current_stage": stage_case.get("current_stage") or portfolio_case.get("stage"),
            "stage_age_hours": stage_age,
            "stage_overdue": stage_overdue,
            "stage_overdue_by_hours": round(stage_age - stage_limit, 2) if stage_overdue else 0.0,
            "assignment_age_hours": assignment_age,
            "assignment_overdue": assignment_overdue,
            "assignment_overdue_by_hours": round(assignment_age - assignment_limit, 2) if assignment_overdue else 0.0,
            "blocked": blocked,
            "blocking_reason": blocking_reason,
            "blockers": blockers,
            "owner": portfolio_case.get("latest_actor"),
            "assigned_reviewers": reviewers,
            "active_assignment_count": len(assignments),
            "review_states": sorted({str(item.get("review_state")) for item in assignments}),
            "next_expected_action": stage_case.get("next_expected_action") or "review_case_status",
            "remediation_links": {
                **links,
                "supervisor_queue": f"/case-intelligence-review/supervisor-queue?case_id={case_id}",
                "reviewer_queue": "/case-intelligence-review/my-assignments",
            },
        })

    queue.sort(key=lambda item: (
        -item["severity_rank"],
        -(item["stage_overdue_by_hours"] + item["assignment_overdue_by_hours"]),
        item["case_id"],
    ))
    counts = {
        "total": len(queue),
        "critical": sum(1 for item in queue if item["severity"] == "critical"),
        "high": sum(1 for item in queue if item["severity"] == "high"),
        "medium": sum(1 for item in queue if item["severity"] == "medium"),
        "low": sum(1 for item in queue if item["severity"] == "low"),
        "blocked": sum(1 for item in queue if item["blocked"]),
        "stage_overdue": sum(1 for item in queue if item["stage_overdue"]),
        "assignment_overdue": sum(1 for item in queue if item["assignment_overdue"]),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if queue else "clear",
        "thresholds": {
            "stage_overdue_hours": stage_limit,
            "assignment_overdue_hours": assignment_limit,
        },
        "counts": counts,
        "queue": queue,
        "source_records_mutated": False,
        "queue_record_created": False,
        "next_action": "remediate_highest_priority_case" if queue else "monitor_portfolio",
    }
