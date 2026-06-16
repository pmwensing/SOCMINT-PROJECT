from __future__ import annotations

import datetime as dt
import os
import statistics
from collections import Counter, defaultdict
from typing import Any

from .portfolio_blocked_overdue_queue_v24_3 import build_blocked_overdue_case_queue
from .portfolio_case_stage_overview_v24_1 import (
    STAGES,
    _event_stage,
    _parse,
    build_case_status_stage_overview,
)
from .portfolio_operations_dashboard_v24_0 import _case_events, build_portfolio_operations_dashboard
from .portfolio_workload_monitoring_v24_2 import build_workload_assignment_monitoring

SCHEMA = "socmint.portfolio_operational_metrics.v24_5"
VERSION = "v24.5.0"


def _windows() -> list[int]:
    raw = os.getenv("SOCMINT_PORTFOLIO_TREND_WINDOWS", "7,30,90")
    values = []
    for item in raw.split(","):
        try:
            value = int(item.strip())
        except ValueError:
            continue
        if value > 0 and value not in values:
            values.append(value)
    return sorted(values) or [7, 30, 90]


def _rate(numerator: int, denominator: int) -> float:
    return round((numerator / denominator * 100.0), 2) if denominator else 0.0


def _duration_summary(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "average_hours": round(statistics.fmean(values), 2) if values else None,
        "median_hours": round(statistics.median(values), 2) if values else None,
        "minimum_hours": round(min(values), 2) if values else None,
        "maximum_hours": round(max(values), 2) if values else None,
    }


def _completed_stage_durations(events: list[dict[str, Any]]) -> dict[str, list[float]]:
    transitions = []
    previous = "unstarted"
    for event in events:
        stage = _event_stage(event)
        occurred = _parse(event.get("occurred_at"))
        if occurred is None or stage == previous:
            continue
        transitions.append((stage, occurred))
        previous = stage
    durations: dict[str, list[float]] = defaultdict(list)
    for index in range(len(transitions) - 1):
        stage, entered = transitions[index]
        _, exited = transitions[index + 1]
        durations[stage].append(max(0.0, (exited - entered).total_seconds() / 3600.0))
    return durations


def build_operational_metrics(
    *, now: dt.datetime | None = None
) -> dict[str, Any]:
    current_time = now or dt.datetime.now(dt.UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=dt.UTC)

    portfolio = build_portfolio_operations_dashboard()
    stage_overview = build_case_status_stage_overview(now=current_time)
    workload = build_workload_assignment_monitoring(now=current_time)
    blocked_queue = build_blocked_overdue_case_queue()
    grouped = _case_events()

    cases = list(portfolio.get("cases") or [])
    case_count = len(cases)
    stage_counts = Counter(item.get("current_stage") for item in stage_overview.get("cases") or [])
    closure_count = sum(1 for item in cases if item.get("stage") in {"closed", "archived", "reopened"})
    archive_count = sum(1 for item in cases if item.get("stage") in {"archived", "reopened"})
    reopen_count = sum(1 for item in cases if item.get("stage") == "reopened")
    completed_count = sum(1 for item in cases if item.get("stage") in {"delivered", "closed", "archived", "reopened"})
    blocked_count = int(portfolio.get("counts", {}).get("blocked") or 0)
    overdue_case_ids = {item.get("case_id") for item in blocked_queue.get("queue") or [] if item.get("stage_overdue") or item.get("assignment_overdue")}

    durations: dict[str, list[float]] = defaultdict(list)
    stage_throughput = Counter()
    event_times: list[tuple[dt.datetime, str, str]] = []
    for case_id, events in grouped.items():
        for stage, values in _completed_stage_durations(events).items():
            durations[stage].extend(values)
        seen = set()
        for event in events:
            stage = _event_stage(event)
            occurred = _parse(event.get("occurred_at"))
            if occurred is not None:
                event_times.append((occurred, case_id, stage))
            marker = (stage, event.get("occurred_at"))
            if marker not in seen:
                stage_throughput[stage] += 1
                seen.add(marker)

    stage_duration_metrics = {
        stage: _duration_summary(durations.get(stage, []))
        for stage in STAGES
    }

    reviewer_throughput = []
    for reviewer in workload.get("reviewers") or []:
        completed = int(reviewer.get("reviewed") or 0) + int(reviewer.get("accepted") or 0)
        reviewer_throughput.append({
            "reviewer": reviewer.get("reviewer"),
            "completed_reviews": completed,
            "active_workload": int(reviewer.get("active_workload") or 0),
            "total_assigned": int(reviewer.get("total_assigned") or 0),
            "completion_rate_percent": _rate(completed, int(reviewer.get("total_assigned") or 0)),
            "average_assignment_age_hours": reviewer.get("average_assignment_age_hours"),
        })
    reviewer_throughput.sort(key=lambda item: (-item["completed_reviews"], str(item["reviewer"])))

    trend_windows = []
    for days in _windows():
        start = current_time - dt.timedelta(days=days)
        window_events = [(time, case_id, stage) for time, case_id, stage in event_times if start <= time <= current_time]
        active_cases = {case_id for _, case_id, _ in window_events}
        window_stages = Counter(stage for _, _, stage in window_events)
        trend_windows.append({
            "days": days,
            "window_start": start.isoformat(),
            "window_end": current_time.isoformat(),
            "event_count": len(window_events),
            "active_case_count": len(active_cases),
            "stage_throughput": dict(sorted(window_stages.items())),
            "closure_completions": window_stages.get("closed", 0),
            "archive_completions": window_stages.get("archived", 0),
            "reopen_completions": window_stages.get("reopened", 0),
        })

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "generated_at": current_time.isoformat(),
        "case_volume": {
            "total_cases": case_count,
            "active_cases": int(portfolio.get("counts", {}).get("active") or 0),
            "completed_cases": completed_count,
            "blocked_cases": blocked_count,
            "overdue_cases": len(overdue_case_ids),
        },
        "completion_counts": {
            "delivered": int(portfolio.get("counts", {}).get("delivered") or 0),
            "closed": closure_count,
            "archived": archive_count,
            "reopened": reopen_count,
        },
        "stage_throughput": dict(sorted(stage_throughput.items())),
        "current_stage_counts": dict(sorted(stage_counts.items())),
        "stage_duration_metrics": stage_duration_metrics,
        "reviewer_throughput": reviewer_throughput,
        "rates": {
            "blocked_rate_percent": _rate(blocked_count, case_count),
            "overdue_rate_percent": _rate(len(overdue_case_ids), case_count),
            "closure_archive_conversion_percent": _rate(archive_count, closure_count),
            "reopen_rate_percent": _rate(reopen_count, archive_count),
        },
        "trend_windows": trend_windows,
        "source_records_mutated": False,
        "metrics_record_created": False,
        "next_action": "review_operational_metrics",
    }
