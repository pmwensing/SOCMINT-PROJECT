from __future__ import annotations

import json
from typing import Any

from . import database as db
from .normalization_review_queue_v13 import loads_dict

SCHEMA = "socmint.normalization_promote_confirmed.v13_15"


def _payload(source: str, item_id: int, evidence_ref: str | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {
        "promoted_from": source,
        "source_id": item_id,
        "evidence_refs": [evidence_ref] if evidence_ref else [],
    }
    if extra:
        data["source_payload"] = extra
    return data


def promote_observation(observation_id: int) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    try:
        item = session.query(db.SpineObservation).filter_by(id=observation_id).first()
        if not item:
            return {"schema": SCHEMA, "kind": "observation", "id": observation_id, "status": "not_found"}
        payload = loads_dict(item.payload_json)
        if payload.get("review_state", "unreviewed") != "confirmed":
            return {"schema": SCHEMA, "kind": "observation", "id": observation_id, "status": "skipped", "reason": "not_confirmed"}
        subject_id = item.subject_id
        assertion_type = item.observation_type
        normalized_value = item.normalized_value
        confidence = item.confidence
        evidence_ref = item.evidence_ref
    finally:
        session.close()

    assertion_id = db.upsert_spine_assertion(
        subject_id=subject_id,
        assertion_type=assertion_type,
        normalized_value=normalized_value,
        confidence=confidence,
        validation_state="confirmed",
        payload=_payload("observation", observation_id, evidence_ref, payload),
    )
    return {
        "schema": SCHEMA,
        "kind": "observation",
        "id": observation_id,
        "status": "promoted",
        "assertion_id": assertion_id,
    }


def promote_account_discovery(discovery_id: int) -> dict[str, Any]:
    item = db.get_account_discovery(discovery_id)
    if not item:
        return {"schema": SCHEMA, "kind": "account_discovery", "id": discovery_id, "status": "not_found"}
    if item.review_state != "confirmed":
        return {"schema": SCHEMA, "kind": "account_discovery", "id": discovery_id, "status": "skipped", "reason": "not_confirmed"}
    payload = json.loads(item.payload_json or "{}")
    assertion_id = db.upsert_spine_assertion(
        subject_id=item.subject_id,
        assertion_type=item.discovery_type,
        normalized_value=item.account_value,
        confidence=item.confidence,
        validation_state="confirmed",
        payload=_payload("account_discovery", discovery_id, item.profile_url, payload),
    )
    db.update_account_discovery_review(
        discovery_id=discovery_id,
        review_state="confirmed",
        actor=item.actor,
        promoted_seed_id=item.promoted_seed_id,
    )
    return {
        "schema": SCHEMA,
        "kind": "account_discovery",
        "id": discovery_id,
        "status": "promoted",
        "assertion_id": assertion_id,
    }


def promote_confirmed_item(kind: str, item_id: int) -> dict[str, Any]:
    if kind == "observation":
        return promote_observation(item_id)
    if kind == "account_discovery":
        return promote_account_discovery(item_id)
    raise ValueError("Invalid promotion kind.")
