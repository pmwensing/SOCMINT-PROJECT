from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.user_account_administration.v28_1"
VERSION = "v28.1.0"
ACTIONS = (
    "administration_user_created",
    "administration_user_activated",
    "administration_user_suspended",
    "administration_user_updated",
    "administration_user_password_reset",
)
ALLOWED_ROLES = ("viewer", "analyst", "reviewer", "supervisor", "admin")


def blocked(key: str) -> dict[str, Any]:
    return {"schema": SCHEMA, "version": VERSION, "status": "blocked", "blockers": [{"key": key}], "user_records_mutated": False, "case_access_scope_changed": False}


def snapshot(user) -> dict[str, Any]:
    return {"user_id": user.id, "username": user.username, "role": user.role, "is_admin": bool(user.is_admin), "is_active": bool(user.is_active), "created_at": user.created_at.isoformat() if user.created_at else None}


def history(username: str | None = None) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        query = session.query(database.AuditLog).filter(database.AuditLog.action.in_(ACTIONS))
        if username:
            query = query.filter(database.AuditLog.target_value == username)
        rows = query.order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc()).all()
        return [{**_json_details(row), "audit_record_id": row.id, "actor": row.actor, "action": row.action, "target_username": row.target_value, "recorded_at": row.created_at.isoformat() if row.created_at else None} for row in rows]
    finally:
        session.close()


def record(session, *, actor: str, action: str, username: str, reason: str, before: dict[str, Any] | None, after: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    binding = {"actor": actor, "action": action, "target_username": username, "reason": reason, "before": before, "after": after}
    digest = _sha(binding)
    event = {"schema": SCHEMA, "version": VERSION, "account_event_id": f"account-event-{digest[:24]}", "account_event_sha256": digest, "reason": reason, "before": before, "after": after, "password_or_hash_logged": False, "case_access_scope_changed": False}
    row = database.AuditLog(actor=actor, action=action, target_value=username, ip_address=ip_address, details=_canonical(event))
    session.add(row)
    session.commit()
    session.refresh(row)
    return {**event, "audit_record_id": row.id, "actor": actor, "action": action, "target_username": username, "recorded_at": row.created_at.isoformat() if row.created_at else None}
