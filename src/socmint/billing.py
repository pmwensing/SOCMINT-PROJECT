from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets
from typing import Any

from sqlalchemy import text

from . import database as db
from .membership import PLAN_DEFINITIONS
from .membership import assign_membership
from .membership import ensure_default_membership
from .membership import membership_summary

BILLING_SCHEMA = "socmint.billing.v8_3_0"
GRACE_DAYS = 3

PLAN_PRICE_IDS = {
    "weekly": "price_socmint_weekly",
    "starter": "price_socmint_starter",
    "pro": "price_socmint_pro",
    "team": "price_socmint_team",
}

PRICE_ID_TO_PLAN = {value: key for key, value in PLAN_PRICE_IDS.items()}


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def ensure_billing_schema() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS billing_events (
                id INTEGER PRIMARY KEY,
                provider VARCHAR(64) NOT NULL,
                provider_event_id VARCHAR(255) NOT NULL UNIQUE,
                event_type VARCHAR(128) NOT NULL,
                username VARCHAR(255),
                plan_key VARCHAR(64),
                status VARCHAR(64) NOT NULL,
                payload_json TEXT NOT NULL,
                processed_at DATETIME NOT NULL,
                created_at DATETIME NOT NULL
            )
        """)
        )
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS checkout_sessions (
                id INTEGER PRIMARY KEY,
                checkout_id VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(255) NOT NULL,
                plan_key VARCHAR(64) NOT NULL,
                status VARCHAR(64) NOT NULL,
                success_url TEXT,
                cancel_url TEXT,
                provider_payload_json TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        )
        session.commit()
    finally:
        session.close()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def create_checkout_session(
    username: str,
    plan_key: str,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    ensure_billing_schema()
    if plan_key not in PLAN_PRICE_IDS:
        raise ValueError("Checkout requires a paid plan.")
    ensure_default_membership(username, actor="billing")
    now = _now()
    checkout_id = "cs_test_" + secrets.token_urlsafe(18)
    payload = {
        "provider": "stripe_stub",
        "mode": "subscription",
        "price_id": PLAN_PRICE_IDS[plan_key],
        "plan_key": plan_key,
        "username": username,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    session = db.Session()
    try:
        session.execute(
            text("""
                INSERT INTO checkout_sessions
                (checkout_id, username, plan_key, status, success_url, cancel_url,
                 provider_payload_json, created_at, updated_at)
                VALUES (:checkout_id, :username, :plan_key, 'created', :success_url,
                        :cancel_url, :provider_payload_json, :now, :now)
            """),
            {
                "checkout_id": checkout_id,
                "username": username,
                "plan_key": plan_key,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "provider_payload_json": _json(payload),
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="checkout_session_create",
        actor=username,
        details={"checkout_id": checkout_id, "plan_key": plan_key},
    )
    return {
        "schema": BILLING_SCHEMA,
        "checkout_id": checkout_id,
        "plan": plan_key,
        "payload": payload,
    }


def record_billing_event(
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
    username: str | None = None,
    plan_key: str | None = None,
    status: str = "processed",
    provider: str = "stripe_stub",
) -> dict[str, Any]:
    ensure_billing_schema()
    now = _now()
    session = db.Session()
    try:
        existing = (
            session.execute(
                text(
                    "SELECT id FROM billing_events WHERE provider_event_id = :provider_event_id"
                ),
                {"provider_event_id": provider_event_id},
            )
            .mappings()
            .first()
        )
        if existing:
            return {
                "schema": BILLING_SCHEMA,
                "duplicate": True,
                "event_id": existing["id"],
            }
        session.execute(
            text("""
                INSERT INTO billing_events
                (provider, provider_event_id, event_type, username, plan_key, status,
                 payload_json, processed_at, created_at)
                VALUES (:provider, :provider_event_id, :event_type, :username,
                        :plan_key, :status, :payload_json, :now, :now)
            """),
            {
                "provider": provider,
                "provider_event_id": provider_event_id,
                "event_type": event_type,
                "username": username,
                "plan_key": plan_key,
                "status": status,
                "payload_json": _json(payload),
                "now": now,
            },
        )
        session.commit()
        row = (
            session.execute(
                text(
                    "SELECT id FROM billing_events WHERE provider_event_id = :provider_event_id"
                ),
                {"provider_event_id": provider_event_id},
            )
            .mappings()
            .first()
        )
        return {"schema": BILLING_SCHEMA, "duplicate": False, "event_id": row["id"]}
    finally:
        session.close()


def process_subscription_event(event: dict[str, Any]) -> dict[str, Any]:
    ensure_billing_schema()
    event_id = str(event.get("id") or event.get("provider_event_id") or "")
    event_type = str(event.get("type") or event.get("event_type") or "")
    data = event.get("data") or event
    username = (
        data.get("username")
        or data.get("customer_email")
        or data.get("client_reference_id")
    )
    price_id = data.get("price_id") or data.get("stripe_price_id")
    plan_key = (
        data.get("plan") or data.get("plan_key") or PRICE_ID_TO_PLAN.get(price_id)
    )
    if not event_id or not event_type:
        raise ValueError("Billing event requires id and type.")
    recorded = record_billing_event(
        event_id, event_type, event, username=username, plan_key=plan_key
    )
    if recorded.get("duplicate"):
        return {**recorded, "action": "ignored_duplicate"}
    if not username:
        return {**recorded, "action": "recorded_unmatched"}

    if event_type in {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "invoice.paid",
    }:
        if not plan_key or plan_key not in PLAN_DEFINITIONS or plan_key == "free":
            raise ValueError("Paid subscription event requires a paid plan.")
        summary = assign_membership(
            username, plan_key, actor="billing", metadata={"source_event": event_id}
        )
        return {**recorded, "action": "membership_activated", "membership": summary}

    if event_type in {"invoice.payment_failed", "customer.subscription.past_due"}:
        summary = mark_past_due(username, actor="billing", source_event=event_id)
        return {**recorded, "action": "membership_past_due", "membership": summary}

    if event_type in {
        "customer.subscription.deleted",
        "customer.subscription.canceled",
    }:
        summary = downgrade_to_free(username, actor="billing", source_event=event_id)
        return {**recorded, "action": "membership_downgraded", "membership": summary}

    return {**recorded, "action": "recorded_no_membership_change"}


def _set_membership_status(
    username: str,
    status: str,
    plan_key: str | None = None,
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_billing_schema()
    user = db.get_user_by_username(username)
    if not user:
        raise ValueError("User not found.")
    now = _now()
    metadata_json = _json(metadata or {})
    session = db.Session()
    try:
        if plan_key:
            session.execute(
                text("""
                    UPDATE user_memberships
                    SET status = :status, plan_key = :plan_key, metadata_json = :metadata_json,
                        actor = :actor, updated_at = :now
                    WHERE user_id = :user_id
                """),
                {
                    "status": status,
                    "plan_key": plan_key,
                    "metadata_json": metadata_json,
                    "actor": actor,
                    "now": now,
                    "user_id": user.id,
                },
            )
        else:
            session.execute(
                text("""
                    UPDATE user_memberships
                    SET status = :status, metadata_json = :metadata_json,
                        actor = :actor, updated_at = :now
                    WHERE user_id = :user_id
                """),
                {
                    "status": status,
                    "metadata_json": metadata_json,
                    "actor": actor,
                    "now": now,
                    "user_id": user.id,
                },
            )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="membership_status_update",
        actor=actor,
        details={"username": username, "status": status, "plan_key": plan_key},
    )
    return membership_summary(username)


def mark_past_due(
    username: str, actor: str | None = None, source_event: str | None = None
) -> dict[str, Any]:
    ensure_default_membership(username, actor=actor)
    grace_until = (_now() + dt.timedelta(days=GRACE_DAYS)).isoformat()
    return _set_membership_status(
        username,
        "past_due_grace",
        actor=actor,
        metadata={"source_event": source_event, "grace_until": grace_until},
    )


def downgrade_to_free(
    username: str, actor: str | None = None, source_event: str | None = None
) -> dict[str, Any]:
    ensure_default_membership(username, actor=actor)
    return _set_membership_status(
        username,
        "active",
        plan_key="free",
        actor=actor,
        metadata={"source_event": source_event, "downgraded_at": _now().isoformat()},
    )


def billing_status(username: str) -> dict[str, Any]:
    ensure_billing_schema()
    summary = ensure_default_membership(username)
    session = db.Session()
    try:
        events = (
            session.execute(
                text("""
                SELECT provider_event_id, event_type, plan_key, status, created_at
                FROM billing_events
                WHERE username = :username
                ORDER BY created_at DESC LIMIT 20
            """),
                {"username": username},
            )
            .mappings()
            .all()
        )
        checkouts = (
            session.execute(
                text("""
                SELECT checkout_id, plan_key, status, created_at
                FROM checkout_sessions
                WHERE username = :username
                ORDER BY created_at DESC LIMIT 20
            """),
                {"username": username},
            )
            .mappings()
            .all()
        )
    finally:
        session.close()
    return {
        "schema": BILLING_SCHEMA,
        "membership": summary,
        "events": [dict(item) for item in events],
        "checkout_sessions": [dict(item) for item in checkouts],
        "plans": {
            key: {"price_id": PLAN_PRICE_IDS.get(key), **value}
            for key, value in PLAN_DEFINITIONS.items()
        },
    }
