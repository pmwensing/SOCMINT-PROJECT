from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.saved_search_views.v27_3"
VERSION = "v27.3.0"
CREATE_ACTION = "saved_search_view_created"
REVISE_ACTION = "saved_search_view_revised"
DEACTIVATE_ACTION = "saved_search_view_deactivated"
ACTIONS = (CREATE_ACTION, REVISE_ACTION, DEACTIVATE_ACTION)
VISIBILITIES = ("private", "shared")


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


def current_views() -> list[dict[str, Any]]:
    views: dict[str, dict[str, Any]] = {}
    for event in history():
        view_id = str(event.get("saved_view_id") or "")
        if event.get("event_type") in {"created", "revised"} and view_id:
            previous = str(event.get("supersedes_saved_view_id") or "")
            if previous in views:
                views[previous] = {
                    **views[previous],
                    "view_status": "superseded",
                    "superseded_by_saved_view_id": view_id,
                }
            views[view_id] = {**event, "view_status": "active"}
        elif event.get("event_type") == "deactivated":
            target = str(event.get("deactivated_saved_view_id") or "")
            if target in views:
                views[target] = {
                    **views[target],
                    "view_status": "deactivated",
                    "deactivation_event_id": event.get("saved_view_event_id"),
                    "deactivated_by": event.get("recorded_by"),
                    "deactivated_at": event.get("recorded_at"),
                    "deactivation_reason": event.get("reason"),
                }
    return sorted(
        views.values(),
        key=lambda item: (
            str(item.get("owner") or ""),
            str(item.get("name") or ""),
            str(item.get("recorded_at") or ""),
        ),
    )


def visible_views(user: str) -> list[dict[str, Any]]:
    return [
        item
        for item in current_views()
        if item.get("owner") == user or item.get("visibility") == "shared"
    ]


def find_view(view_id: str, user: str) -> dict[str, Any] | None:
    return next(
        (item for item in visible_views(user) if item.get("saved_view_id") == view_id),
        None,
    )


def _duplicate(name: str, owner: str, exclude_id: str | None = None) -> bool:
    key = name.lower().strip()
    return any(
        item.get("owner") == owner
        and str(item.get("name") or "").lower().strip() == key
        and item.get("view_status") == "active"
        and item.get("saved_view_id") != exclude_id
        for item in current_views()
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
            target_value=str(event.get("saved_view_id") or ""),
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


def create_view(
    *,
    name: str,
    owner: str,
    query: str,
    filters: dict[str, Any],
    visibility: str,
    description: str = "",
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name, owner, visibility = (
        str(name or "").strip(),
        str(owner or "").strip(),
        str(visibility or "private").strip(),
    )
    if confirmed is not True:
        return blocked("explicit_saved_view_confirmation_required")
    if not name:
        return blocked("saved_view_name_required")
    if not owner:
        return blocked("saved_view_owner_required")
    if visibility not in VISIBILITIES:
        return blocked("saved_view_visibility_invalid")
    if _duplicate(name, owner):
        return blocked("active_saved_view_name_must_be_unique_per_owner")
    definition = {"query": str(query or ""), "filters": dict(filters or {})}
    content = {
        "event_type": "created",
        "name": name,
        "owner": owner,
        "description": str(description or "").strip(),
        "visibility": visibility,
        "definition": definition,
        "definition_sha256": _sha(definition),
        "revision": 1,
        "view_status": "active",
        "supersedes_saved_view_id": None,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "saved_view_id": f"saved-view-{digest[:24]}",
        "saved_view_event_id": f"saved-view-event-{digest[:24]}",
        "saved_view_event_sha256": digest,
        "source_records_mutated": False,
        "case_access_scope_changed": False,
        "saved_view_grants_access": False,
    }
    return {
        **_record(CREATE_ACTION, event, owner, ip_address),
        "status": "saved_view_created",
        "next_action": "run_saved_view",
    }


def revise_view(
    view_id: str,
    *,
    actor: str,
    name: str,
    query: str,
    filters: dict[str, Any],
    visibility: str,
    description: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_view(view_id, actor)
    if previous is None:
        return blocked("saved_view_required")
    if previous.get("owner") != actor:
        return blocked("saved_view_owner_required")
    if previous.get("view_status") != "active":
        return blocked("active_saved_view_required")
    if confirmed is not True:
        return blocked("explicit_saved_view_revision_confirmation_required")
    name, reason, visibility = (
        str(name or "").strip(),
        str(reason or "").strip(),
        str(visibility or "private").strip(),
    )
    if not name:
        return blocked("saved_view_name_required")
    if not reason:
        return blocked("saved_view_revision_reason_required")
    if visibility not in VISIBILITIES:
        return blocked("saved_view_visibility_invalid")
    if _duplicate(name, actor, view_id):
        return blocked("active_saved_view_name_must_be_unique_per_owner")
    definition = {"query": str(query or ""), "filters": dict(filters or {})}
    binding = {
        "saved_view_id": view_id,
        "saved_view_event_id": previous.get("saved_view_event_id"),
        "saved_view_event_sha256": previous.get("saved_view_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
        "revision": previous.get("revision"),
    }
    content = {
        "event_type": "revised",
        "name": name,
        "owner": actor,
        "description": str(description or "").strip(),
        "visibility": visibility,
        "definition": definition,
        "definition_sha256": _sha(definition),
        "revision": int(previous.get("revision") or 1) + 1,
        "reason": reason,
        "view_status": "active",
        "supersedes_saved_view_id": view_id,
        "previous_view_binding": binding,
        "previous_view_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "saved_view_id": f"saved-view-{digest[:24]}",
        "saved_view_event_id": f"saved-view-event-{digest[:24]}",
        "saved_view_event_sha256": digest,
        "source_records_mutated": False,
        "prior_saved_view_mutated": False,
        "case_access_scope_changed": False,
        "saved_view_grants_access": False,
    }
    return {
        **_record(REVISE_ACTION, event, actor, ip_address),
        "status": "saved_view_revised",
        "next_action": "run_saved_view",
    }


def deactivate_view(
    view_id: str,
    *,
    actor: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_view(view_id, actor)
    if previous is None:
        return blocked("saved_view_required")
    if previous.get("owner") != actor:
        return blocked("saved_view_owner_required")
    if previous.get("view_status") != "active":
        return blocked("active_saved_view_required")
    if confirmed is not True:
        return blocked("explicit_saved_view_deactivation_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("saved_view_deactivation_reason_required")
    binding = {
        "saved_view_id": view_id,
        "saved_view_event_id": previous.get("saved_view_event_id"),
        "saved_view_event_sha256": previous.get("saved_view_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
    }
    content = {
        "event_type": "deactivated",
        "deactivated_saved_view_id": view_id,
        "owner": previous.get("owner"),
        "name": previous.get("name"),
        "reason": reason,
        "view_status": "deactivated",
        "saved_view_binding": binding,
        "saved_view_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "saved_view_id": f"saved-view-deactivation-{digest[:24]}",
        "saved_view_event_id": f"saved-view-event-{digest[:24]}",
        "saved_view_event_sha256": digest,
        "source_records_mutated": False,
        "saved_view_mutated": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(DEACTIVATE_ACTION, event, actor, ip_address),
        "status": "saved_view_deactivated",
        "next_action": "review_saved_views",
    }
