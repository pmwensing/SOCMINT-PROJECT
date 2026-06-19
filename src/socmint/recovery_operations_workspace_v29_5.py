from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .recovery_operations_v29_5 import PLAN_TYPES, REQUEST_STATES, current_retry_requests, history, interventions, recovery_plans

SCHEMA = "socmint.recovery_operations_workspace.v29_5"
VERSION = "v29.5.0"


def _parse(value: Any):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_recovery_operations_workspace() -> dict[str, Any]:
    requests = current_retry_requests()
    plans = recovery_plans()
    operator_events = interventions()
    events = history()
    now = datetime.now(timezone.utc)
    request_counts = Counter(str(item.get("request_state") or "unknown") for item in requests)
    pending = [item for item in requests if item.get("request_state") == "pending"]
    approved = [item for item in requests if item.get("request_state") == "approved"]
    executable_window = []
    expired_window = []
    findings = []
    for item in approved:
        earliest = _parse(item.get("earliest_retry_at"))
        window_end = _parse(item.get("retry_window_ends_at"))
        if window_end and now >= window_end:
            expired_window.append(item)
            findings.append({"severity":"high","key":"approved_retry_window_expired","retry_request_id":item.get("retry_request_id")})
        elif not earliest or now >= earliest:
            executable_window.append(item)
        else:
            findings.append({"severity":"low","key":"approved_retry_waiting_for_backoff","retry_request_id":item.get("retry_request_id")})
    plan_job_ids = {str(item.get("collection_job_id") or "") for item in plans}
    for item in approved:
        if str(item.get("collection_job_id") or "") not in plan_job_ids:
            findings.append({"severity":"medium","key":"approved_retry_without_recovery_plan","retry_request_id":item.get("retry_request_id")})
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "request_states": list(REQUEST_STATES),
        "plan_types": list(PLAN_TYPES),
        "retry_requests": requests,
        "retry_request_count": len(requests),
        "retry_request_state_counts": dict(sorted(request_counts.items())),
        "pending_retry_requests": pending,
        "pending_retry_request_count": len(pending),
        "approved_retry_requests": approved,
        "approved_retry_request_count": len(approved),
        "retry_window_open": executable_window,
        "retry_window_open_count": len(executable_window),
        "retry_window_expired": expired_window,
        "retry_window_expired_count": len(expired_window),
        "recovery_plans": plans,
        "recovery_plan_count": len(plans),
        "operator_interventions": operator_events,
        "operator_intervention_count": len(operator_events),
        "recovery_findings": findings,
        "recovery_finding_count": len(findings),
        "recovery_history": events[-300:],
        "recovery_event_count": len(events),
        "connector_execution_available": False,
        "automatic_retry_execution_available": False,
        "legacy_scan_jobs_mutated": False,
        "evidence_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "review_retry_recovery_and_operator_intervention",
    }
