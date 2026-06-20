from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.connector_integration_administration.v28_5"
VERSION = "v28.5.0"
ACTIONS = (
    "administration_connector_registered",
    "administration_connector_revised",
    "administration_connector_enabled",
    "administration_connector_disabled",
    "administration_connector_auth_readiness_updated",
)
AUTH_STATES = (
    "not_configured",
    "configured",
    "expiring",
    "expired",
    "invalid",
    "rotation_required",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "connector_records_mutated": False,
        "connector_execution_performed": False,
        "secret_values_exposed": False,
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
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "source_action": action,
            "target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_connectors() -> list[dict[str, Any]]:
    connectors: dict[str, dict[str, Any]] = {}
    for event in history():
        connector_id = str(event.get("connector_id") or "")
        if not connector_id:
            continue
        event_type = event.get("event_type")
        if event_type in {"connector_registered", "connector_revised"}:
            previous = str(event.get("supersedes_connector_id") or "")
            if previous in connectors:
                connectors[previous] = {
                    **connectors[previous],
                    "connector_status": "superseded",
                    "superseded_by_connector_id": connector_id,
                }
            connectors[connector_id] = {
                **event,
                "connector_status": "active" if event.get("enabled") else "disabled",
            }
        elif connector_id in connectors:
            item = dict(connectors[connector_id])
            if event_type == "connector_enabled":
                item["enabled"] = True
                item["connector_status"] = "active"
            elif event_type == "connector_disabled":
                item["enabled"] = False
                item["connector_status"] = "disabled"
            elif event_type == "connector_auth_readiness_updated":
                item["auth_readiness"] = event.get("auth_readiness")
                item["auth_expires_at"] = event.get("auth_expires_at")
            connectors[connector_id] = item
    return sorted(
        connectors.values(),
        key=lambda item: str((item.get("definition") or {}).get("name") or ""),
    )


def find_connector(connector_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_connectors()
            if item.get("connector_id") == connector_id
        ),
        None,
    )


def register_connector(
    *,
    actor: str,
    name: str,
    connector_type: str,
    authorization_scopes: Any,
    rate_limit_policy: Any,
    description: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name = str(name or "").strip()
    connector_type = str(connector_type or "").strip()
    reason = str(reason or "").strip()
    scopes = sorted(
        {
            str(item).strip()
            for item in (authorization_scopes or [])
            if str(item).strip()
        }
    )
    rate_policy = rate_limit_policy if isinstance(rate_limit_policy, dict) else {}
    if confirmed is not True:
        return blocked("explicit_connector_registration_confirmation_required")
    if not name:
        return blocked("connector_name_required")
    if not connector_type:
        return blocked("connector_type_required")
    if not reason:
        return blocked("administrative_reason_required")
    active_names = {
        str((item.get("definition") or {}).get("name") or "").lower()
        for item in current_connectors()
        if item.get("connector_status") != "superseded"
    }
    if name.lower() in active_names:
        return blocked("connector_name_must_be_unique")
    definition = {
        "name": name,
        "connector_type": connector_type,
        "description": str(description or "").strip(),
        "authorization_scopes": scopes,
        "rate_limit_policy": rate_policy,
    }
    content = {
        "event_type": "connector_registered",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "revision": 1,
        "supersedes_connector_id": None,
        "enabled": False,
        "auth_readiness": "not_configured",
        "auth_expires_at": None,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "connector_id": f"connector-{digest[:24]}",
        "connector_event_id": f"connector-event-{digest[:24]}",
        "connector_event_sha256": digest,
        "secret_values_exposed": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(ACTIONS[0], actor, name, event, ip_address),
        "status": "connector_registered",
        "next_action": "configure_authentication_out_of_band",
    }


def revise_connector(
    connector_id: str,
    *,
    actor: str,
    name: str,
    connector_type: str,
    authorization_scopes: Any,
    rate_limit_policy: Any,
    description: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_connector(connector_id)
    if previous is None or previous.get("connector_status") == "superseded":
        return blocked("current_connector_required")
    if confirmed is not True:
        return blocked("explicit_connector_revision_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    old = previous.get("definition") or {}
    definition = {
        "name": str(name or old.get("name") or "").strip(),
        "connector_type": str(
            connector_type or old.get("connector_type") or ""
        ).strip(),
        "description": str(description or "").strip(),
        "authorization_scopes": sorted(
            {
                str(item).strip()
                for item in (authorization_scopes or [])
                if str(item).strip()
            }
        ),
        "rate_limit_policy": rate_limit_policy
        if isinstance(rate_limit_policy, dict)
        else {},
    }
    binding = {
        "connector_id": connector_id,
        "connector_event_id": previous.get("connector_event_id"),
        "connector_event_sha256": previous.get("connector_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
        "revision": previous.get("revision"),
    }
    content = {
        "event_type": "connector_revised",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "revision": int(previous.get("revision") or 1) + 1,
        "supersedes_connector_id": connector_id,
        "previous_connector_binding": binding,
        "previous_connector_binding_sha256": _sha(binding),
        "enabled": bool(previous.get("enabled")),
        "auth_readiness": previous.get("auth_readiness") or "not_configured",
        "auth_expires_at": previous.get("auth_expires_at"),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "connector_id": f"connector-{digest[:24]}",
        "connector_event_id": f"connector-event-{digest[:24]}",
        "connector_event_sha256": digest,
        "prior_connector_event_mutated": False,
        "secret_values_exposed": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(ACTIONS[1], actor, definition["name"], event, ip_address),
        "status": "connector_revised",
        "next_action": "review_connector_configuration",
    }


def set_connector_enabled(
    connector_id: str,
    *,
    actor: str,
    enabled: bool,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    connector = find_connector(connector_id)
    if connector is None or connector.get("connector_status") == "superseded":
        return blocked("current_connector_required")
    if confirmed is not True:
        return blocked("explicit_connector_state_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    if bool(connector.get("enabled")) == bool(enabled):
        return blocked("connector_state_unchanged")
    content = {
        "event_type": "connector_enabled" if enabled else "connector_disabled",
        "connector_id": connector_id,
        "enabled": bool(enabled),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "connector_event_id": f"connector-event-{digest[:24]}",
        "connector_event_sha256": digest,
        "secret_values_exposed": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    action = ACTIONS[2] if enabled else ACTIONS[3]
    return {
        **_record(action, actor, connector_id, event, ip_address),
        "status": "connector_state_updated",
        "next_action": "review_connector_health",
    }


def update_auth_readiness(
    connector_id: str,
    *,
    actor: str,
    auth_readiness: str,
    auth_expires_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    connector = find_connector(connector_id)
    if connector is None or connector.get("connector_status") == "superseded":
        return blocked("current_connector_required")
    auth_readiness = str(auth_readiness or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_auth_readiness_confirmation_required")
    if auth_readiness not in AUTH_STATES:
        return blocked("auth_readiness_invalid")
    if not reason:
        return blocked("administrative_reason_required")
    content = {
        "event_type": "connector_auth_readiness_updated",
        "connector_id": connector_id,
        "auth_readiness": auth_readiness,
        "auth_expires_at": str(auth_expires_at or "").strip() or None,
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "connector_event_id": f"connector-event-{digest[:24]}",
        "connector_event_sha256": digest,
        "secret_value_recorded": False,
        "secret_values_exposed": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(ACTIONS[4], actor, connector_id, event, ip_address),
        "status": "connector_auth_readiness_updated",
        "next_action": "review_connector_authentication_state",
    }
