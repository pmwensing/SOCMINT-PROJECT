from __future__ import annotations

from collections import Counter
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha
from .report_builder_events_v27_5 import current_reports, history as report_history
from .report_export_packages_v27_5 import latest_packages
from .saved_search_view_events_v27_3 import current_views, history as saved_view_history
from .watchlist_monitoring_events_v27_4 import current_watchlists, history as watchlist_history

SCHEMA = "socmint.search_reporting_history_audit.v27_6"
VERSION = "v27.6.0"


def _event_family(action: str, event_type: str) -> str:
    text = f"{action} {event_type}".lower()
    if "saved_search_view" in text or "saved_view" in text:
        return "saved_view"
    if "watchlist" in text:
        return "watchlist"
    if "report_package" in text or "package_generated" in text:
        return "report_package"
    if "report" in text:
        return "report_definition"
    return "search"


def _source_bindings(event: dict[str, Any]) -> dict[str, Any]:
    bindings = {}
    for key in (
        "saved_view_binding", "previous_view_binding", "watchlist_binding",
        "report_binding", "previous_report_binding", "executed_access_scope",
    ):
        value = event.get(key)
        if value not in (None, {}, []):
            bindings[key] = value
    return bindings


def _normalize(event: dict[str, Any]) -> dict[str, Any]:
    action = str(event.get("source_action") or "")
    event_type = str(event.get("event_type") or "")
    family = _event_family(action, event_type)
    bindings = _source_bindings(event)
    identifiers = {
        key: event.get(key)
        for key in (
            "saved_view_id", "watchlist_id", "monitoring_run_id", "report_id",
            "report_event_id", "package_id", "package_event_id",
        )
        if event.get(key)
    }
    hashes = {
        key: event.get(key)
        for key in (
            "saved_view_event_sha256", "definition_sha256", "watchlist_event_sha256",
            "result_set_sha256", "previous_result_set_sha256", "report_event_sha256",
            "file_manifest_sha256", "package_sha256",
        )
        if event.get(key)
    }
    normalized = {
        "history_event_id": f"v27-history-{event.get('action_record_id')}",
        "action_record_id": event.get("action_record_id"),
        "family": family,
        "event_type": event_type,
        "source_action": action,
        "actor": event.get("recorded_by"),
        "occurred_at": event.get("recorded_at"),
        "owner": event.get("owner"),
        "status": event.get("status") or event.get("view_status") or event.get("watchlist_status") or event.get("report_status"),
        "identifiers": identifiers,
        "hashes": hashes,
        "source_bindings": bindings,
        "source_bindings_sha256": _sha(bindings),
        "access_scope": event.get("executed_access_scope"),
        "event_counts": {
            "section_count": event.get("section_count"),
            "result_count": event.get("result_count"),
            "added_count": event.get("added_count"),
            "removed_count": event.get("removed_count"),
        },
        "change_detected": event.get("change_detected"),
        "notification_triggered": event.get("notification_triggered"),
        "reason": event.get("reason"),
        "direct_links": {
            "saved_views": "/global-search/saved-views",
            "watchlists": "/global-search/watchlists",
            "reports": "/global-search/reports",
            "advanced_search": "/global-search/advanced",
        },
        "raw_event_sha256": _sha(event),
    }
    return normalized


def build_search_reporting_history_audit(
    *,
    families: list[str] | tuple[str, ...] | set[str] | None = None,
    actors: list[str] | tuple[str, ...] | set[str] | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    requested_families = {str(item) for item in (families or []) if str(item)}
    requested_actors = {str(item) for item in (actors or []) if str(item)}
    source_events = saved_view_history() + watchlist_history() + report_history()
    events = [_normalize(item) for item in source_events]
    if requested_families:
        events = [item for item in events if item["family"] in requested_families]
    if requested_actors:
        events = [item for item in events if str(item.get("actor") or "") in requested_actors]
    events.sort(key=lambda item: (item.get("occurred_at") or "", item.get("action_record_id") or 0))
    safe_limit = max(1, min(int(limit or 500), 2000))
    events = events[-safe_limit:]
    family_counts = Counter(item["family"] for item in events)
    action_counts = Counter(item["source_action"] for item in events)
    actor_counts = Counter(str(item.get("actor") or "unknown") for item in events)
    state = {
        "saved_views": current_views(),
        "watchlists": current_watchlists(),
        "reports": current_reports(),
        "report_packages": latest_packages(),
    }
    state_counts = {
        "saved_view_count": len(state["saved_views"]),
        "active_saved_view_count": sum(item.get("view_status") == "active" for item in state["saved_views"]),
        "watchlist_count": len(state["watchlists"]),
        "active_watchlist_count": sum(item.get("watchlist_status") == "active" for item in state["watchlists"]),
        "report_count": len(state["reports"]),
        "active_report_count": sum(item.get("report_status") == "active" for item in state["reports"]),
        "report_package_count": len(state["report_packages"]),
    }
    core = {"events": [item["history_event_id"] for item in events], "state_counts": state_counts}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "events": events,
        "event_count": len(events),
        "family_counts": dict(sorted(family_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "actor_counts": dict(sorted(actor_counts.items())),
        "current_state": state,
        "current_state_counts": state_counts,
        "history_sha256": _sha(core),
        "filters": {"families": sorted(requested_families), "actors": sorted(requested_actors), "limit": safe_limit},
        "read_only": True,
        "source_records_mutated": False,
        "history_events_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "review_search_reporting_history",
    }
