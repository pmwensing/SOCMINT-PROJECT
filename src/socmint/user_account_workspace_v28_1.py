from __future__ import annotations

from typing import Any

from . import database
from .user_account_events_v28_1 import ALLOWED_ROLES, SCHEMA, VERSION, history, snapshot


def build_user_account_workspace() -> dict[str, Any]:
    database.ensure_configured()
    session = database.Session()
    try:
        users = [snapshot(item) for item in session.query(database.User).order_by(database.User.username.asc()).all()]
    finally:
        session.close()
    events = history()
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "users": users,
        "user_count": len(users),
        "active_user_count": sum(bool(item["is_active"]) for item in users),
        "suspended_user_count": sum(not bool(item["is_active"]) for item in users),
        "administrator_count": sum(bool(item["is_admin"]) for item in users),
        "roles": list(ALLOWED_ROLES),
        "account_history": events[-100:],
        "account_event_count": len(events),
        "credentials_visible": False,
        "credential_hashes_visible": False,
        "case_access_scope_changed": False,
        "next_action": "review_or_manage_user_accounts",
    }


def actor_is_administrator(username: str) -> bool:
    database.ensure_configured()
    session = database.Session()
    try:
        user = session.query(database.User).filter(database.User.username == username).first()
        return bool(user and user.is_active and user.is_admin)
    finally:
        session.close()
