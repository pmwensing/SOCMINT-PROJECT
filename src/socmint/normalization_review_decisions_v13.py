from __future__ import annotations

import json
from typing import Any

from . import database as db

SCHEMA = "socmint.normalization_review_decision.v13_8"
ALLOWED_DECISIONS = {"confirmed", "rejected", "suppressed", "unreviewed"}


def _load_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def review_observation(
    observation_id: int,
    decision: str,
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("Invalid review decision.")
    db.ensure_configured()
    session = db.Session()
    try:
        item = session.query(db.SpineObservation).filter_by(id=observation_id).first()
        if not item:
            return {
                "schema": SCHEMA,
                "kind": "observation",
                "id": observation_id,
                "status": "not_found",
            }
        payload = _load_payload(item.payload_json)
        payload["review_state"] = decision
        payload["review"] = {"actor": actor, "note": note, "decision": decision}
        item.payload_json = json.dumps(payload, sort_keys=True)
        session.commit()
        return {
            "schema": SCHEMA,
            "kind": "observation",
            "id": observation_id,
            "status": "updated",
            "review_state": decision,
        }
    finally:
        session.close()


def review_account_discovery(
    discovery_id: int, decision: str, actor: str | None = None, note: str | None = None
) -> dict[str, Any]:
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("Invalid review decision.")
    updated = db.update_account_discovery_review(
        discovery_id=discovery_id,
        review_state=decision,
        actor=actor,
        note=note,
    )
    if not updated:
        return {
            "schema": SCHEMA,
            "kind": "account_discovery",
            "id": discovery_id,
            "status": "not_found",
        }
    return {
        "schema": SCHEMA,
        "kind": "account_discovery",
        "id": discovery_id,
        "status": "updated",
        "review_state": decision,
    }


def apply_normalization_review_decision(
    kind: str,
    item_id: int,
    decision: str,
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if kind == "observation":
        return review_observation(item_id, decision, actor=actor, note=note)
    if kind == "account_discovery":
        return review_account_discovery(item_id, decision, actor=actor, note=note)
    raise ValueError("Invalid review item kind.")
