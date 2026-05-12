from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from . import database as db

MEMBERSHIP_SCHEMA = "socmint.membership.v8_2_0"

PLAN_DEFINITIONS: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Free",
        "price": "$0",
        "limits": {
            "active_cases": 1,
            "subjects_per_month": 3,
            "connector_runs_per_day": 10,
            "browser_captures_per_day": 2,
            "account_ingests_per_day": 2,
            "signed_exports_per_month": 0,
            "graph_builds_per_day": 1,
            "storage_gb": 0.25,
            "team_seats": 1,
            "watermark_exports": True,
        },
    },
    "weekly": {
        "name": "Weekly",
        "price": "$9/week",
        "limits": {
            "active_cases": 3,
            "subjects_per_month": 15,
            "connector_runs_per_day": 60,
            "browser_captures_per_day": 20,
            "account_ingests_per_day": 20,
            "signed_exports_per_month": 3,
            "graph_builds_per_day": 10,
            "storage_gb": 2,
            "team_seats": 1,
            "watermark_exports": False,
        },
    },
    "starter": {
        "name": "Starter",
        "price": "$29/month",
        "limits": {
            "active_cases": 10,
            "subjects_per_month": 50,
            "connector_runs_per_day": 150,
            "browser_captures_per_day": 50,
            "account_ingests_per_day": 75,
            "signed_exports_per_month": 10,
            "graph_builds_per_day": 25,
            "storage_gb": 10,
            "team_seats": 1,
            "watermark_exports": False,
        },
    },
    "pro": {
        "name": "Pro",
        "price": "$79/month",
        "limits": {
            "active_cases": 50,
            "subjects_per_month": 250,
            "connector_runs_per_day": 800,
            "browser_captures_per_day": 300,
            "account_ingests_per_day": 400,
            "signed_exports_per_month": 100,
            "graph_builds_per_day": 150,
            "storage_gb": 100,
            "team_seats": 1,
            "watermark_exports": False,
        },
    },
    "team": {
        "name": "Team",
        "price": "$199/month",
        "limits": {
            "active_cases": 200,
            "subjects_per_month": 1000,
            "connector_runs_per_day": 3000,
            "browser_captures_per_day": 1000,
            "account_ingests_per_day": 1200,
            "signed_exports_per_month": 500,
            "graph_builds_per_day": 500,
            "storage_gb": 500,
            "team_seats": 3,
            "watermark_exports": False,
        },
    },
}

ACTION_QUOTA_KEYS = {
    "case_create": "active_cases",
    "subject_create": "subjects_per_month",
    "connector_run": "connector_runs_per_day",
    "browser_capture": "browser_captures_per_day",
    "account_discovery_ingest": "account_ingests_per_day",
    "signed_export": "signed_exports_per_month",
    "graph_build": "graph_builds_per_day",
}


@dataclass(frozen=True)
class Period:
    key: str
    starts_at: dt.datetime
    resets_at: dt.datetime


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def _now() -> dt.datetime:
    return db.utc_now()


def _period_for_quota(quota_key: str, now: dt.datetime | None = None) -> Period:
    now = now or _now()
    if quota_key.endswith("_per_day") or quota_key == "graph_builds_per_day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reset = start + dt.timedelta(days=1)
        return Period(start.date().isoformat(), start, reset)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        reset = start.replace(year=start.year + 1, month=1)
    else:
        reset = start.replace(month=start.month + 1)
    return Period(start.strftime("%Y-%m"), start, reset)


def ensure_membership_schema() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS membership_plans (
                id INTEGER PRIMARY KEY,
                plan_key VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(128) NOT NULL,
                price_label VARCHAR(64) NOT NULL,
                entitlements_json TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_memberships (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                plan_key VARCHAR(64) NOT NULL,
                status VARCHAR(64) NOT NULL,
                period_started_at DATETIME,
                period_ends_at DATETIME,
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255),
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(user_id)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                action VARCHAR(128) NOT NULL,
                quota_key VARCHAR(128) NOT NULL,
                amount INTEGER NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS usage_counters (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                quota_key VARCHAR(128) NOT NULL,
                period_key VARCHAR(64) NOT NULL,
                used INTEGER NOT NULL,
                reset_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(user_id, quota_key, period_key)
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS quota_overrides (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                quota_key VARCHAR(128) NOT NULL,
                limit_value INTEGER,
                reason TEXT,
                actor VARCHAR(255),
                expires_at DATETIME,
                created_at DATETIME NOT NULL
            )
        """))
        session.commit()
    finally:
        session.close()
    seed_default_plans()


def seed_default_plans() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        now = _now()
        for plan_key, plan in PLAN_DEFINITIONS.items():
            existing = session.execute(
                text("SELECT id FROM membership_plans WHERE plan_key = :plan_key"),
                {"plan_key": plan_key},
            ).first()
            params = {
                "plan_key": plan_key,
                "name": plan["name"],
                "price_label": plan["price"],
                "entitlements_json": _json(plan["limits"]),
                "created_at": now,
            }
            if existing:
                session.execute(
                    text("""
                        UPDATE membership_plans
                        SET name = :name, price_label = :price_label,
                            entitlements_json = :entitlements_json, is_active = 1
                        WHERE plan_key = :plan_key
                    """),
                    params,
                )
            else:
                session.execute(
                    text("""
                        INSERT INTO membership_plans
                        (plan_key, name, price_label, entitlements_json, is_active, created_at)
                        VALUES (:plan_key, :name, :price_label, :entitlements_json, 1, :created_at)
                    """),
                    params,
                )
        session.commit()
    finally:
        session.close()


def _user_id(username: str) -> int:
    user = db.get_user_by_username(username)
    if not user:
        raise ValueError("User not found.")
    return int(user.id)


def ensure_default_membership(username: str, actor: str | None = None) -> dict[str, Any]:
    ensure_membership_schema()
    user_id = _user_id(username)
    session = db.Session()
    try:
        existing = session.execute(
            text("SELECT * FROM user_memberships WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
        if not existing:
            now = _now()
            session.execute(
                text("""
                    INSERT INTO user_memberships
                    (user_id, plan_key, status, period_started_at, period_ends_at,
                     metadata_json, actor, created_at, updated_at)
                    VALUES (:user_id, 'free', 'active', :now, NULL, '{}', :actor, :now, :now)
                """),
                {"user_id": user_id, "actor": actor or "system", "now": now},
            )
            session.commit()
        return membership_summary(username)
    finally:
        session.close()


def assign_membership(username: str, plan_key: str, actor: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_membership_schema()
    if plan_key not in PLAN_DEFINITIONS:
        raise ValueError(f"Unknown plan: {plan_key}")
    user_id = _user_id(username)
    now = _now()
    session = db.Session()
    try:
        session.execute(
            text("""
                INSERT INTO user_memberships
                (user_id, plan_key, status, period_started_at, period_ends_at,
                 metadata_json, actor, created_at, updated_at)
                VALUES (:user_id, :plan_key, 'active', :now, NULL, :metadata_json, :actor, :now, :now)
                ON CONFLICT(user_id) DO UPDATE SET
                    plan_key = excluded.plan_key,
                    status = excluded.status,
                    period_started_at = excluded.period_started_at,
                    period_ends_at = excluded.period_ends_at,
                    metadata_json = excluded.metadata_json,
                    actor = excluded.actor,
                    updated_at = excluded.updated_at
            """),
            {
                "user_id": user_id,
                "plan_key": plan_key,
                "metadata_json": _json(metadata or {}),
                "actor": actor,
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="membership_assign",
        actor=actor,
        details={"username": username, "plan_key": plan_key},
    )
    return membership_summary(username)


def _membership_row(user_id: int) -> dict[str, Any]:
    session = db.Session()
    try:
        row = session.execute(
            text("SELECT * FROM user_memberships WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
        if not row:
            return {}
        return dict(row)
    finally:
        session.close()


def _limits_for_plan(plan_key: str) -> dict[str, Any]:
    return dict(PLAN_DEFINITIONS.get(plan_key, PLAN_DEFINITIONS["free"])["limits"])


def _override_limit(user_id: int, quota_key: str) -> int | None:
    now = _now()
    session = db.Session()
    try:
        row = session.execute(
            text("""
                SELECT limit_value FROM quota_overrides
                WHERE user_id = :user_id AND quota_key = :quota_key
                  AND (expires_at IS NULL OR expires_at > :now)
                ORDER BY created_at DESC, id DESC LIMIT 1
            """),
            {"user_id": user_id, "quota_key": quota_key, "now": now},
        ).mappings().first()
        return None if not row else row["limit_value"]
    finally:
        session.close()


def usage_for_quota(user_id: int, quota_key: str) -> dict[str, Any]:
    ensure_membership_schema()
    if quota_key == "active_cases":
        session = db.Session()
        try:
            try:
                used = session.execute(
                    text("SELECT COUNT(*) AS c FROM case_records WHERE status != 'closed'"),
                ).mappings().first()["c"]
            except Exception:
                used = 0
            return {"used": int(used), "period_key": "lifetime", "resets_at": None}
        finally:
            session.close()
    period = _period_for_quota(quota_key)
    session = db.Session()
    try:
        row = session.execute(
            text("""
                SELECT used, reset_at FROM usage_counters
                WHERE user_id = :user_id AND quota_key = :quota_key AND period_key = :period_key
            """),
            {"user_id": user_id, "quota_key": quota_key, "period_key": period.key},
        ).mappings().first()
        if not row:
            return {"used": 0, "period_key": period.key, "resets_at": period.resets_at.isoformat()}
        return {"used": int(row["used"]), "period_key": period.key, "resets_at": str(row["reset_at"])}
    finally:
        session.close()


def record_usage(username: str, action: str, quota_key: str, amount: int = 1, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_membership_schema()
    user_id = _user_id(username)
    period = _period_for_quota(quota_key)
    now = _now()
    session = db.Session()
    try:
        if quota_key != "active_cases":
            session.execute(
                text("""
                    INSERT INTO usage_counters
                    (user_id, quota_key, period_key, used, reset_at, updated_at)
                    VALUES (:user_id, :quota_key, :period_key, :amount, :reset_at, :now)
                    ON CONFLICT(user_id, quota_key, period_key) DO UPDATE SET
                        used = usage_counters.used + excluded.used,
                        reset_at = excluded.reset_at,
                        updated_at = excluded.updated_at
                """),
                {
                    "user_id": user_id,
                    "quota_key": quota_key,
                    "period_key": period.key,
                    "amount": int(amount),
                    "reset_at": period.resets_at,
                    "now": now,
                },
            )
        session.execute(
            text("""
                INSERT INTO usage_events
                (user_id, action, quota_key, amount, metadata_json, created_at)
                VALUES (:user_id, :action, :quota_key, :amount, :metadata_json, :now)
            """),
            {
                "user_id": user_id,
                "action": action,
                "quota_key": quota_key,
                "amount": int(amount),
                "metadata_json": _json(metadata or {}),
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    return usage_for_quota(user_id, quota_key)


def set_quota_override(username: str, quota_key: str, limit_value: int, actor: str | None = None, reason: str | None = None, expires_at: dt.datetime | None = None) -> dict[str, Any]:
    ensure_membership_schema()
    user_id = _user_id(username)
    session = db.Session()
    try:
        session.execute(
            text("""
                INSERT INTO quota_overrides
                (user_id, quota_key, limit_value, reason, actor, expires_at, created_at)
                VALUES (:user_id, :quota_key, :limit_value, :reason, :actor, :expires_at, :now)
            """),
            {
                "user_id": user_id,
                "quota_key": quota_key,
                "limit_value": int(limit_value),
                "reason": reason,
                "actor": actor,
                "expires_at": expires_at,
                "now": _now(),
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="quota_override",
        actor=actor,
        details={"username": username, "quota_key": quota_key, "limit_value": limit_value, "reason": reason},
    )
    return membership_summary(username)


def membership_summary(username: str) -> dict[str, Any]:
    ensure_membership_schema()
    user_id = _user_id(username)
    row = _membership_row(user_id)
    plan_key = row.get("plan_key") or "free"
    limits = _limits_for_plan(plan_key)
    usage = {}
    for quota_key, limit in limits.items():
        if isinstance(limit, bool):
            usage[quota_key] = {"limit": limit, "used": None, "remaining": None, "resets_at": None}
            continue
        actual_limit = _override_limit(user_id, quota_key)
        if actual_limit is None:
            actual_limit = limit
        used_payload = usage_for_quota(user_id, quota_key)
        used = used_payload["used"]
        usage[quota_key] = {
            "limit": actual_limit,
            "used": used,
            "remaining": None if actual_limit is None else max(int(actual_limit) - int(used), 0),
            "resets_at": used_payload.get("resets_at"),
            "period_key": used_payload.get("period_key"),
        }
    return {
        "schema": MEMBERSHIP_SCHEMA,
        "username": username,
        "user_id": user_id,
        "plan": plan_key,
        "status": row.get("status") or "active",
        "limits": limits,
        "usage": usage,
        "membership": row,
    }


def evaluate_gate(
    username: str,
    action: str,
    quota_key: str | None = None,
    amount: int = 1,
    scope_state: str = "authorized",
    metadata: dict[str, Any] | None = None,
    consume: bool = False,
) -> dict[str, Any]:
    quota_key = quota_key or ACTION_QUOTA_KEYS.get(action)
    summary = ensure_default_membership(username)
    if scope_state != "authorized":
        result = {
            "allowed": False,
            "user_id": summary["user_id"],
            "plan": summary["plan"],
            "action": action,
            "quota_key": quota_key,
            "used": None,
            "limit": None,
            "resets_at": None,
            "scope_state": scope_state,
            "upgrade_required": False,
            "reason": "Responsible-use scope is not authorized.",
        }
        db.record_audit_event(action="gate_block_scope", actor=username, details=result)
        return result
    if not quota_key:
        return {
            "allowed": True,
            "user_id": summary["user_id"],
            "plan": summary["plan"],
            "action": action,
            "quota_key": None,
            "used": None,
            "limit": None,
            "resets_at": None,
            "scope_state": scope_state,
            "upgrade_required": False,
            "reason": "Allowed; no quota mapped.",
        }
    quota = summary["usage"].get(quota_key) or {}
    limit = quota.get("limit")
    used = quota.get("used") or 0
    allowed = limit is None or isinstance(limit, bool) or int(used) + int(amount) <= int(limit)
    result = {
        "allowed": bool(allowed),
        "user_id": summary["user_id"],
        "plan": summary["plan"],
        "action": action,
        "quota_key": quota_key,
        "used": used,
        "limit": limit,
        "resets_at": quota.get("resets_at"),
        "scope_state": scope_state,
        "upgrade_required": not allowed,
        "reason": "Allowed." if allowed else f"Quota exceeded for {quota_key}.",
    }
    if not allowed:
        db.record_audit_event(action="gate_block_quota", actor=username, details=result)
        return result
    if consume:
        record_usage(username, action, quota_key, amount=amount, metadata=metadata)
        result["used"] = int(used) + int(amount)
    return result


def list_memberships() -> dict[str, Any]:
    ensure_membership_schema()
    session = db.Session()
    try:
        rows = session.execute(
            text("""
                SELECT u.username, u.role, u.is_admin, u.is_active,
                       COALESCE(m.plan_key, 'free') AS plan_key,
                       COALESCE(m.status, 'active') AS status,
                       m.updated_at
                FROM users u
                LEFT JOIN user_memberships m ON m.user_id = u.id
                ORDER BY u.created_at DESC
            """),
        ).mappings().all()
        return {"schema": MEMBERSHIP_SCHEMA, "memberships": [dict(row) for row in rows], "plans": PLAN_DEFINITIONS}
    finally:
        session.close()
