from __future__ import annotations

import secrets
from typing import Any

from werkzeug.security import generate_password_hash

from . import database
from .user_account_events_v28_1 import ACTIONS, ALLOWED_ROLES, SCHEMA, VERSION, blocked, record, snapshot


def _active_admin_count(session) -> int:
    return session.query(database.User).filter(database.User.is_admin.is_(True), database.User.is_active.is_(True)).count()


def provision_user(*, actor: str, username: str, role: str, is_admin: bool, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    username = str(username or "").strip()
    role = str(role or "viewer").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_user_provisioning_confirmation_required")
    if not username:
        return blocked("username_required")
    if role not in ALLOWED_ROLES:
        return blocked("role_invalid")
    if not reason:
        return blocked("administrative_reason_required")
    database.ensure_configured()
    session = database.Session()
    try:
        if session.query(database.User).filter(database.User.username == username).first():
            return blocked("username_already_exists")
        internal_secret = secrets.token_urlsafe(48)
        user = database.User(
            username=username,
            password_hash=generate_password_hash(internal_secret),
            role="admin" if is_admin else role,
            is_admin=bool(is_admin),
            is_active=False,
        )
        session.add(user)
        session.flush()
        after = snapshot(user)
        event = record(session, actor=actor, action=ACTIONS[0], username=username, reason=reason, before=None, after=after, ip_address=ip_address)
        return {"schema": SCHEMA, "version": VERSION, "status": "user_provisioned", "user": after, "account_event": event, "credential_returned": False, "credential_hash_returned": False, "activation_required": True, "case_access_scope_changed": False, "next_action": "complete_secure_credential_onboarding"}
    finally:
        session.close()


def update_user(username: str, *, actor: str, role: str | None = None, is_admin: bool | None = None, is_active: bool | None = None, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    if confirmed is not True:
        return blocked("explicit_user_update_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    if role is not None and role not in ALLOWED_ROLES:
        return blocked("role_invalid")
    database.ensure_configured()
    session = database.Session()
    try:
        user = session.query(database.User).filter(database.User.username == username).first()
        if user is None:
            return blocked("user_required")
        before = snapshot(user)
        desired_admin = bool(is_admin) if is_admin is not None else bool(user.is_admin)
        desired_active = bool(is_active) if is_active is not None else bool(user.is_active)
        if user.is_admin and user.is_active and (not desired_admin or not desired_active) and _active_admin_count(session) <= 1:
            return blocked("last_active_administrator_must_be_preserved")
        if role is not None:
            user.role = role
        if is_admin is not None:
            user.is_admin = bool(is_admin)
            if user.is_admin:
                user.role = "admin"
        if is_active is not None:
            user.is_active = bool(is_active)
        session.flush()
        after = snapshot(user)
        if before == after:
            return blocked("account_state_unchanged")
        if before["is_active"] is False and after["is_active"] is True:
            action = ACTIONS[1]
        elif before["is_active"] is True and after["is_active"] is False:
            action = ACTIONS[2]
        else:
            action = ACTIONS[3]
        event = record(session, actor=actor, action=action, username=username, reason=reason, before=before, after=after, ip_address=ip_address)
        return {"schema": SCHEMA, "version": VERSION, "status": "user_updated", "user": after, "account_event": event, "prior_user_snapshot_mutated": False, "case_access_scope_changed": False, "next_action": "review_user_account"}
    finally:
        session.close()
