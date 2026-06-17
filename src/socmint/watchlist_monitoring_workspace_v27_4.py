from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha
from .saved_search_views_workspace_v27_3 import run_saved_view
from .watchlist_monitoring_events_v27_4 import (
    SCHEMA,
    VERSION,
    blocked,
    current_watchlists,
    find_watchlist,
    history,
    next_due_at,
    visible_watchlists,
    _record,
    ACTIONS,
)


def _result_ids(execution: dict[str, Any]) -> list[str]:
    payload = execution.get("execution") or {}
    return sorted(str(item.get("result_id")) for item in payload.get("results") or [] if item.get("result_id"))


def _previous_run(watchlist_id: str) -> dict[str, Any] | None:
    runs = [item for item in history() if item.get("event_type") == "run" and item.get("watchlist_id") == watchlist_id]
    return runs[-1] if runs else None


def _notification(rule: str, added: list[str], removed: list[str], old_count: int, new_count: int) -> bool:
    if rule == "new_results":
        return bool(added)
    if rule == "removed_results":
        return bool(removed)
    if rule == "result_count_change":
        return old_count != new_count
    return bool(added or removed or old_count != new_count)


def run_watchlist_monitoring(
    watchlist_id: str,
    *,
    user_identity: str,
    allowed_case_ids: set[str] | None = None,
    limit: int = 100,
    ip_address: str | None = None,
) -> dict[str, Any]:
    watchlist = find_watchlist(watchlist_id, user_identity)
    if watchlist is None:
        return blocked("watchlist_required")
    if watchlist.get("watchlist_status") != "active":
        return blocked("active_watchlist_required")
    saved_view_id = str((watchlist.get("saved_view_binding") or {}).get("saved_view_id") or "")
    execution = run_saved_view(
        saved_view_id,
        user_identity=user_identity,
        allowed_case_ids=allowed_case_ids,
        limit=limit,
    )
    if execution.get("status") != "saved_view_executed":
        return blocked("saved_view_execution_failed")
    current_ids = _result_ids(execution)
    previous = _previous_run(watchlist_id)
    previous_ids = sorted(str(item) for item in (previous or {}).get("result_ids") or [])
    added = sorted(set(current_ids) - set(previous_ids))
    removed = sorted(set(previous_ids) - set(current_ids))
    previous_count = len(previous_ids)
    result_count = len(current_ids)
    rule = str(watchlist.get("notification_rule") or "any_change")
    notify = _notification(rule, added, removed, previous_count, result_count)
    binding = {
        "watchlist_id": watchlist_id,
        "watchlist_event_id": watchlist.get("watchlist_event_id"),
        "watchlist_event_sha256": watchlist.get("watchlist_event_sha256"),
        "saved_view_id": saved_view_id,
        "saved_view_definition_sha256": (watchlist.get("saved_view_binding") or {}).get("definition_sha256"),
    }
    content = {
        "event_type": "run",
        "watchlist_id": watchlist_id,
        "owner": user_identity,
        "monitoring_run_sequence": int((previous or {}).get("monitoring_run_sequence") or 0) + 1,
        "result_ids": current_ids,
        "result_count": result_count,
        "result_set_sha256": _sha(current_ids),
        "previous_result_set_sha256": (previous or {}).get("result_set_sha256"),
        "added_result_ids": added,
        "removed_result_ids": removed,
        "added_count": len(added),
        "removed_count": len(removed),
        "change_detected": bool(added or removed or previous_count != result_count),
        "notification_rule": rule,
        "notification_triggered": notify,
        "executed_access_scope": execution.get("execution", {}).get("access_scope"),
        "watchlist_binding": binding,
        "watchlist_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "monitoring_run_id": f"watchlist-run-{digest[:24]}",
        "watchlist_event_id": f"watchlist-event-{digest[:24]}",
        "watchlist_event_sha256": digest,
        "source_records_mutated": False,
        "saved_view_mutated": False,
        "watchlist_mutated": False,
        "case_access_scope_changed": False,
        "watchlist_grants_access": False,
    }
    recorded = _record(ACTIONS[3], event, user_identity, ip_address)
    return {
        **recorded,
        "status": "watchlist_monitoring_completed",
        "execution": execution.get("execution"),
        "next_action": "review_watchlist_changes" if content["change_detected"] else "await_next_watchlist_run",
    }


def build_watchlist_workspace(user_identity: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    watchlists = visible_watchlists(user_identity)
    projected = []
    for item in watchlists:
        due_at = next_due_at(item, now)
        due = bool(
            item.get("watchlist_status") == "active"
            and due_at
            and datetime.fromisoformat(due_at.replace("Z", "+00:00")) <= now
        )
        projected.append({**item, "next_due_at": due_at, "monitoring_due": due})
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "user_identity": user_identity,
        "watchlists": projected,
        "watchlist_count": len(projected),
        "active_watchlist_count": sum(item.get("watchlist_status") == "active" for item in projected),
        "paused_watchlist_count": sum(item.get("watchlist_status") == "paused" for item in projected),
        "due_watchlist_count": sum(bool(item.get("monitoring_due")) for item in projected),
        "notification_pending_count": sum(bool(item.get("last_notification_triggered")) for item in projected),
        "monitoring_run_count": sum(item.get("event_type") == "run" for item in history()),
        "read_only_workspace": True,
        "source_records_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "run_due_watchlists",
    }
