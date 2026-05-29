from __future__ import annotations

import json
from typing import Any

from . import database as db

SCHEMA = "socmint.normalization_review_queue.v13_14"


def loads_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def confidence_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def observation_item(item) -> dict[str, Any]:
    payload = loads_dict(item.payload_json)
    return {
        "kind": "observation",
        "id": item.id,
        "subject_id": item.subject_id,
        "run_id": item.run_id,
        "type": item.observation_type,
        "value": item.normalized_value,
        "confidence": item.confidence,
        "source": item.source_ref,
        "evidence_ref": item.evidence_ref,
        "review_state": payload.get("review_state", "unreviewed"),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def account_item(item) -> dict[str, Any]:
    return {
        "kind": "account_discovery",
        "id": item.id,
        "subject_id": item.subject_id,
        "run_id": None,
        "type": item.discovery_type,
        "value": item.account_value,
        "confidence": item.confidence,
        "source": item.platform,
        "evidence_ref": item.profile_url,
        "review_state": item.review_state,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def filter_queue_items(
    items: list[dict[str, Any]],
    review_state: str | None = None,
    kind: str | None = None,
    min_confidence: float | None = None,
) -> list[dict[str, Any]]:
    if review_state:
        items = [item for item in items if item["review_state"] == review_state]
    if kind:
        items = [item for item in items if item["kind"] == kind]
    if min_confidence is not None:
        items = [
            item
            for item in items
            if confidence_float(item.get("confidence")) >= min_confidence
        ]
    return items


def build_normalization_review_queue(
    subject_id: int | None = None,
    review_state: str | None = None,
    kind: str | None = None,
    min_confidence: float | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        observations_query = session.query(db.SpineObservation)
        accounts_query = session.query(db.AccountDiscovery)
        if subject_id is not None:
            observations_query = observations_query.filter_by(subject_id=subject_id)
            accounts_query = accounts_query.filter_by(subject_id=subject_id)
        observations = (
            observations_query.order_by(db.SpineObservation.created_at.desc())
            .limit(limit)
            .all()
        )
        accounts = (
            accounts_query.order_by(db.AccountDiscovery.created_at.desc())
            .limit(limit)
            .all()
        )
        items = [observation_item(item) for item in observations]
        items.extend(account_item(item) for item in accounts)
        items = filter_queue_items(
            items,
            review_state=review_state,
            kind=kind,
            min_confidence=min_confidence,
        )
        items = sorted(items, key=lambda item: item.get("created_at") or "", reverse=True)
        items = items[:limit]
        counts: dict[str, int] = {}
        for item in items:
            state = item["review_state"]
            counts[state] = counts.get(state, 0) + 1
        return {
            "schema": SCHEMA,
            "subject_id": subject_id,
            "review_state": review_state,
            "kind": kind,
            "min_confidence": min_confidence,
            "count": len(items),
            "state_counts": counts,
            "items": items,
        }
    finally:
        session.close()
