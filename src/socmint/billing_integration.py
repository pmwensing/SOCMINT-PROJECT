from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import text

from . import database as db
from .billing import BILLING_SCHEMA
from .billing import PLAN_PRICE_IDS
from .billing import PRICE_ID_TO_PLAN
from .billing import process_subscription_event
from .membership import assign_membership
from .membership import ensure_default_membership
from .membership import membership_summary

BILLING_INTEGRATION_SCHEMA = "socmint.billing_integration.v9_1_0"


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def ensure_billing_integration_schema() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS billing_customer_links (
                id INTEGER PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                provider VARCHAR(64) NOT NULL,
                customer_id VARCHAR(255) NOT NULL,
                subscription_id VARCHAR(255),
                plan_key VARCHAR(64),
                status VARCHAR(64) NOT NULL,
                current_period_end DATETIME,
                metadata_json TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """)
        )
        session.commit()
    finally:
        session.close()


def link_customer(
    username: str,
    customer_id: str,
    subscription_id: str | None = None,
    plan_key: str | None = None,
    status: str = "active",
    provider: str = "stripe",
    current_period_end: dt.datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_billing_integration_schema()
    ensure_default_membership(username, actor="billing")
    now = _now()
    session = db.Session()
    try:
        session.execute(
            text("""
                INSERT INTO billing_customer_links
                (username, provider, customer_id, subscription_id, plan_key, status,
                 current_period_end, metadata_json, created_at, updated_at)
                VALUES (:username, :provider, :customer_id, :subscription_id, :plan_key,
                        :status, :current_period_end, :metadata_json, :now, :now)
                ON CONFLICT(username) DO UPDATE SET
                    provider = excluded.provider,
                    customer_id = excluded.customer_id,
                    subscription_id = excluded.subscription_id,
                    plan_key = excluded.plan_key,
                    status = excluded.status,
                    current_period_end = excluded.current_period_end,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
            """),
            {
                "username": username,
                "provider": provider,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "plan_key": plan_key,
                "status": status,
                "current_period_end": current_period_end,
                "metadata_json": _json(metadata or {}),
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    if plan_key and status in {"active", "trialing"}:
        assign_membership(
            username,
            plan_key,
            actor="billing",
            metadata={"customer_id": customer_id, "subscription_id": subscription_id},
        )
    db.record_audit_event(
        action="billing_customer_link",
        actor="billing",
        details={
            "username": username,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "plan_key": plan_key,
            "status": status,
        },
    )
    return billing_link_status(username)


def billing_link_status(username: str) -> dict[str, Any]:
    ensure_billing_integration_schema()
    session = db.Session()
    try:
        row = (
            session.execute(
                text("SELECT * FROM billing_customer_links WHERE username = :username"),
                {"username": username},
            )
            .mappings()
            .first()
        )
    finally:
        session.close()
    return {
        "schema": BILLING_INTEGRATION_SCHEMA,
        "username": username,
        "linked": bool(row),
        "link": dict(row) if row else None,
        "membership": membership_summary(username),
        "billing_schema": BILLING_SCHEMA,
    }


def normalize_provider_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("type") or event.get("event_type") or ""
    data = (
        event.get("data", {}).get("object")
        if isinstance(event.get("data"), dict) and "object" in event.get("data", {})
        else event.get("data", event)
    )
    if not isinstance(data, dict):
        data = {}
    customer_id = data.get("customer") or data.get("customer_id")
    subscription_id = (
        data.get("subscription") or data.get("subscription_id") or data.get("id")
    )
    username = (
        data.get("client_reference_id")
        or data.get("username")
        or data.get("customer_email")
    )
    price_id = data.get("price_id")
    items = (
        data.get("items", {}).get("data", [])
        if isinstance(data.get("items"), dict)
        else []
    )
    if not price_id and items:
        first_price = items[0].get("price", {}) if isinstance(items[0], dict) else {}
        price_id = first_price.get("id")
    plan_key = (
        data.get("plan") or data.get("plan_key") or PRICE_ID_TO_PLAN.get(price_id)
    )
    current_period_end = data.get("current_period_end")
    if isinstance(current_period_end, int):
        current_period_end_dt = dt.datetime.fromtimestamp(
            current_period_end, tz=dt.timezone.utc
        )
    else:
        current_period_end_dt = None
    return {
        "event_id": event.get("id") or event.get("provider_event_id"),
        "event_type": event_type,
        "username": username,
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "price_id": price_id,
        "plan_key": plan_key,
        "status": data.get("status") or "active",
        "current_period_end": current_period_end_dt,
        "raw": event,
    }


def process_provider_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_provider_event(event)
    mapped = {
        "id": normalized["event_id"],
        "type": normalized["event_type"],
        "data": {
            "username": normalized["username"],
            "plan": normalized["plan_key"],
            "price_id": normalized["price_id"],
        },
    }
    result = process_subscription_event(mapped)
    if normalized.get("username") and normalized.get("customer_id"):
        link = link_customer(
            normalized["username"],
            normalized["customer_id"],
            subscription_id=normalized.get("subscription_id"),
            plan_key=normalized.get("plan_key"),
            status=normalized.get("status") or "active",
            current_period_end=normalized.get("current_period_end"),
            metadata={"source_event": normalized.get("event_id")},
        )
    else:
        link = None
    return {
        "schema": BILLING_INTEGRATION_SCHEMA,
        "normalized": {k: v for k, v in normalized.items() if k != "raw"},
        "billing_result": result,
        "customer_link": link,
    }


def billing_provider_config() -> dict[str, Any]:
    return {
        "schema": BILLING_INTEGRATION_SCHEMA,
        "provider": "stripe-compatible",
        "configured_price_ids": PLAN_PRICE_IDS,
        "requires": [
            "STRIPE_SECRET_KEY",
            "SOCMINT_BILLING_WEBHOOK_SECRET",
            "customer portal configuration",
            "test-mode webhook replay before live mode",
        ],
    }
