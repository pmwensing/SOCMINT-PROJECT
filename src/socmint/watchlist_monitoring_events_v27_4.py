from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .saved_search_view_events_v27_3 import find_view

SCHEMA = "socmint.watchlist_monitoring.v27_4"
VERSION = "v27.4.0"
ACTIONS = (
    "search_watchlist_created",
    "search_watchlist_paused",
    "search_watchlist_resumed",
    "search_watchlist_run_recorded",
)
CADENCES = ("manual", "hourly", "daily", "weekly")
NOTIFY_RULES = ("any_change", "new_results", "removed_results", "result_count_change")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "case_access_scope_changed": False,
    }


def history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "action_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "source_action": row.action,
            }
            for row in rows
        ]
    finally:
        session.close()


def current_watchlists() -> list[dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for event in history():
        watchlist_id = str(event.get("watchlist_id") or "")
        if not watchlist_id:
            continue
        event_type = event.get("event_type")
        if event_type == "created":
            items[watchlist_id] = {**event, "watchlist_status": "active"}
        elif watchlist_id in items and event_type in {"paused", "resumed"}:
            items[watchlist_id] = {
                **items[watchlist_id],
                "watchlist_status": "paused" if event_type == "paused" else "active",
                "last_status_event_id": event.get("watchlist_event_id"),
                "last_status_reason": event.get("reason"),
                "last_status_at": event.get("recorded_at"),
            }
        elif watchlist_id in items and event_type == "run":
            items[watchlist_id] = {
                **items[watchlist_id],
                "last_run_id": event.get("monitoring_run_id"),
                "last_run_at": event.get("recorded_at"),
                "last_result_count": event.get("result_count"),
                "last_result_set_sha256": event.get("result_set_sha256"),
                "last_change_detected": event.get("change_detected"),
                "last_notification_triggered": event.get("notification_triggered"),
            }
    return sorted(
        items.values(),
        key=lambda item: (str(item.get("owner") or ""), str(item.get("name") or "")),
    )


def visible_watchlists(user: str) -> list[dict[str, Any]]:
    return [item for item in current_watchlists() if item.get("owner") == user]


def find_watchlist(watchlist_id: str, user: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in visible_watchlists(user)
            if item.get("watchlist_id") == watchlist_id
        ),
        None,
    )


def _record(
    action: str, event: dict[str, Any], actor: str, ip: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=str(event.get("watchlist_id") or ""),
            ip_address=ip,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "action_record_id": row.id,
            "recorded_by": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _duplicate(name: str, owner: str) -> bool:
    key = name.strip().lower()
    return any(
        item.get("owner") == owner
        and str(item.get("name") or "").strip().lower() == key
        for item in current_watchlists()
    )


def create_watchlist(
    *,
    name: str,
    owner: str,
    saved_view_id: str,
    cadence: str,
    notification_rule: str,
    description: str = "",
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name = str(name or "").strip()
    owner = str(owner or "").strip()
    cadence = str(cadence or "manual").strip()
    notification_rule = str(notification_rule or "any_change").strip()
    view = find_view(saved_view_id, owner)
    if confirmed is not True:
        return blocked("explicit_watchlist_confirmation_required")
    if not name:
        return blocked("watchlist_name_required")
    if view is None or view.get("view_status") != "active":
        return blocked("active_visible_saved_view_required")
    if cadence not in CADENCES:
        return blocked("watchlist_cadence_invalid")
    if notification_rule not in NOTIFY_RULES:
        return blocked("watchlist_notification_rule_invalid")
    if _duplicate(name, owner):
        return blocked("watchlist_name_must_be_unique_per_owner")
    binding = {
        "saved_view_id": view.get("saved_view_id"),
        "saved_view_event_id": view.get("saved_view_event_id"),
        "saved_view_event_sha256": view.get("saved_view_event_sha256"),
        "definition_sha256": view.get("definition_sha256"),
    }
    content = {
        "event_type": "created",
        "name": name,
        "owner": owner,
        "description": str(description or "").strip(),
        "cadence": cadence,
        "notification_rule": notification_rule,
        "saved_view_binding": binding,
        "saved_view_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "watchlist_id": f"watchlist-{digest[:24]}",
        "watchlist_event_id": f"watchlist-event-{digest[:24]}",
        "watchlist_event_sha256": digest,
        "source_records_mutated": False,
        "saved_view_mutated": False,
        "case_access_scope_changed": False,
        "watchlist_grants_access": False,
    }
    result = _record(ACTIONS[0], event, owner, ip_address)
    return {
        **result,
        "status": "watchlist_created",
        "next_action": "run_watchlist_monitoring",
    }


def set_watchlist_status(
    watchlist_id: str,
    *,
    actor: str,
    status: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    watchlist = find_watchlist(watchlist_id, actor)
    event_type = (
        "paused" if status == "paused" else "resumed" if status == "active" else ""
    )
    if watchlist is None:
        return blocked("watchlist_required")
    if confirmed is not True:
        return blocked("explicit_watchlist_status_confirmation_required")
    if not event_type:
        return blocked("watchlist_status_invalid")
    if watchlist.get("watchlist_status") == status:
        return blocked("watchlist_status_unchanged")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("watchlist_status_reason_required")
    binding = {
        "watchlist_id": watchlist_id,
        "watchlist_event_id": watchlist.get("watchlist_event_id"),
        "watchlist_event_sha256": watchlist.get("watchlist_event_sha256"),
    }
    content = {
        "event_type": event_type,
        "watchlist_id": watchlist_id,
        "owner": actor,
        "reason": reason,
        "watchlist_binding": binding,
        "watchlist_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "watchlist_event_id": f"watchlist-event-{digest[:24]}",
        "watchlist_event_sha256": digest,
        "source_records_mutated": False,
        "watchlist_mutated": False,
        "case_access_scope_changed": False,
    }
    action = ACTIONS[1] if event_type == "paused" else ACTIONS[2]
    result = _record(action, event, actor, ip_address)
    return {
        **result,
        "status": f"watchlist_{event_type}",
        "next_action": "review_watchlist_monitoring",
    }


def next_due_at(watchlist: dict[str, Any], now: datetime | None = None) -> str | None:
    cadence = watchlist.get("cadence")
    if cadence == "manual":
        return None
    base_text = watchlist.get("last_run_at") or watchlist.get("recorded_at")
    if not base_text:
        return None
    base = datetime.fromisoformat(str(base_text).replace("Z", "+00:00"))
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    delta = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "weekly": timedelta(days=7),
    }[cadence]
    return (base.astimezone(timezone.utc) + delta).isoformat()
