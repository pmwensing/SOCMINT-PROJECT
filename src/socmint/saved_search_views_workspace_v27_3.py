from __future__ import annotations

from typing import Any

from .advanced_search_filters_v27_2 import build_advanced_search_filters
from .saved_search_view_events_v27_3 import SCHEMA, VERSION, VISIBILITIES, blocked, find_view, history, visible_views


def run_saved_view(view_id: str, *, user_identity: str, allowed_case_ids: set[str] | None = None, limit: int = 100) -> dict[str, Any]:
    view = find_view(view_id, user_identity)
    if view is None or view.get("view_status") != "active":
        return blocked("active_visible_saved_view_required")
    definition = dict(view.get("definition") or {})
    filters = dict(definition.get("filters") or {})
    filters["allowed_case_ids"] = allowed_case_ids
    filters["limit"] = limit
    execution = build_advanced_search_filters(str(definition.get("query") or ""), **filters)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "saved_view_executed",
        "saved_view": view,
        "execution": execution,
        "executed_with_current_access_scope": True,
        "saved_view_grants_access": False,
        "source_records_mutated": False,
        "saved_view_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "review_saved_view_results",
    }


def build_saved_views_workspace(user_identity: str) -> dict[str, Any]:
    visible = visible_views(user_identity)
    active = [item for item in visible if item.get("view_status") == "active"]
    owned = [item for item in active if item.get("owner") == user_identity]
    shared = [item for item in active if item.get("owner") != user_identity and item.get("visibility") == "shared"]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "user_identity": user_identity,
        "visibilities": list(VISIBILITIES),
        "saved_views": visible,
        "active_saved_views": active,
        "owned_saved_views": owned,
        "shared_saved_views": shared,
        "saved_view_count": len(visible),
        "active_saved_view_count": len(active),
        "owned_saved_view_count": len(owned),
        "shared_saved_view_count": len(shared),
        "history_count": len(history()),
        "read_only_workspace": True,
        "source_records_mutated": False,
        "case_access_scope_changed": False,
        "next_action": "create_or_run_saved_view",
    }
