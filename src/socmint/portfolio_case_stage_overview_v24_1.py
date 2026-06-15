from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from .portfolio_operations_dashboard_v24_0 import _case_events, _configured_case_ids

SCHEMA = "socmint.portfolio_case_stage_overview.v24_1"
VERSION = "v24.1.0"

STAGES = (
    "unstarted",
    "active",
    "closure_review",
    "dossier_exported",
    "delivered",
    "closed",
    "retention_pending_archive",
    "archived",
    "reopened",
)

STAGE_ACTIONS = {
    "case_reopen_authorization": "reopened",
    "case_archive_package_generated": "archived",
    "case_retention_policy_assignment": "retention_pending_archive",
    "case_supervisor_closure_decision": "closed",
    "dossier_recipient_acknowledgement": "delivered",
    "dossier_delivery_receipt": "delivered",
    "dossier_final_export_package": "dossier_exported",
    "case_closure_readiness_review": "closure_review",
}

NEXT_ACTIONS = {
    "unstarted": "begin_case_review",
    "active": "complete_case_analysis",
    "closure_review": "record_supervisor_closure_decision",
    "dossier_exported": "complete_secure_delivery",
    "delivered": "begin_case_closure_review",
    "closed": "assign_retention_policy",
    "retention_pending_archive": "generate_case_archive_package",
    "archived": "monitor_retention_or_request_reopen",
    "reopened": "resume_case_operations",
}


def _parse(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    except (TypeError, ValueError):
        return None


def _event_stage(event: dict[str, Any]) -> str:
    action = str(event.get("action") or "")
    details = event.get("details") or {}
    if action == "case_reopen_authorization" and details.get("decision") != "authorize":
        return "archived"
    if action == "case_supervisor_closure_decision" and details.get("decision") != "close":
        return "closure_review"
    return STAGE_ACTIONS.get(action, "active")


def normalize_case_stage(
    case_id: str,
    events: list[dict[str, Any]],
    *,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.UTC)
    transitions: list[dict[str, Any]] = []
    last_stage = "unstarted"
    for event in events:
        stage = _event_stage(event)
        if stage != last_stage:
            transitions.append({
                "stage": stage,
                "entered_at": event.get("occurred_at"),
                "source_action": event.get("action"),
                "source_record_id": event.get("record_id"),
            })
            last_stage = stage

    current_stage = transitions[-1]["stage"] if transitions else "unstarted"
    prior_stage = transitions[-2]["stage"] if len(transitions) > 1 else None
    entered_at = transitions[-1]["entered_at"] if transitions else None
    entered_dt = _parse(entered_at)
    duration_seconds = max(0, int((now - entered_dt).total_seconds())) if entered_dt else None

    blockers = []
    for event in events:
        details = event.get("details") or {}
        for blocker in details.get("blockers") or []:
            key = str(blocker.get("key") or "portfolio_attention_required")
            if key not in {item["key"] for item in blockers}:
                blockers.append({"key": key, "source_action": event.get("action")})
    blocking_reason = blockers[0]["key"] if blockers else None

    position = STAGES.index(current_stage) + 1
    return {
        "case_id": case_id,
        "current_stage": current_stage,
        "prior_stage": prior_stage,
        "stage_entered_at": entered_at,
        "stage_duration_seconds": duration_seconds,
        "stage_duration_hours": round(duration_seconds / 3600, 2) if duration_seconds is not None else None,
        "progress_position": position,
        "progress_total": len(STAGES),
        "progress_percent": round(position / len(STAGES) * 100, 1),
        "blocked": bool(blockers),
        "blocking_reason": blocking_reason,
        "blockers": blockers,
        "next_expected_action": (
            "resolve_blocking_reason" if blockers else NEXT_ACTIONS[current_stage]
        ),
        "transitions": transitions,
        "latest_activity_at": events[-1].get("occurred_at") if events else None,
    }


def build_case_status_stage_overview(
    *, now: dt.datetime | None = None
) -> dict[str, Any]:
    grouped = _case_events()
    case_ids = sorted(set(grouped) | set(_configured_case_ids()))
    cases = [normalize_case_stage(case_id, grouped.get(case_id, []), now=now) for case_id in case_ids]
    counts = Counter(item["current_stage"] for item in cases)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "stage_model": list(STAGES),
        "stage_counts": dict(sorted(counts.items())),
        "cases": sorted(cases, key=lambda item: (item["progress_position"], item["case_id"])),
        "case_count": len(cases),
        "blocked_count": sum(1 for item in cases if item["blocked"]),
        "source_records_mutated": False,
        "stage_record_created": False,
        "next_action": "review_case_stage_overview",
    }
