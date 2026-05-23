from __future__ import annotations

import json
from typing import Any

from . import database as db
from .alias_promotion_gates_v12_10_7_1 import promotion_gate_for_observation

SCHEMA = "socmint.legacy_assertion_scrubber.v12_10_7_2"

BLOCKED_ASSERTION_TYPES = {
    "static_asset_url",
    "avatar_url",
    "asset_artifact_url",
    "metadata_artifact",
    "platform_artifact_id",
}

BAD_IDENTITY_ASSERTION_TYPES = {
    "profile_url",
    "url",
    "phone",
}


def safe_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return {} if fallback is None else fallback
    try:
        return json.loads(value)
    except Exception:
        return {} if fallback is None else fallback


def assertion_promotion_gate(assertion: dict[str, Any]) -> dict[str, Any]:
    assertion_type = assertion.get("type") or assertion.get("assertion_type")
    value = assertion.get("value") or assertion.get("normalized_value")
    gate = promotion_gate_for_observation({"type": assertion_type, "value": value})

    blocked = bool(gate.get("blocked")) or assertion_type in BLOCKED_ASSERTION_TYPES
    reason_labels = list(gate.get("reason_labels") or [])

    if assertion_type in BLOCKED_ASSERTION_TYPES and not reason_labels:
        if assertion_type in {"avatar_url", "static_asset_url", "asset_artifact_url"}:
            reason_labels.append("rejected_asset_only_url")
        elif assertion_type == "metadata_artifact":
            reason_labels.append("rejected_timestamp")
        elif assertion_type == "platform_artifact_id":
            reason_labels.append("rejected_platform_artifact_id")

    safe_type = gate.get("safe_type") or assertion_type

    return {
        "schema": SCHEMA,
        "blocked": blocked,
        "original_type": assertion_type,
        "safe_type": safe_type,
        "reason_labels": sorted(set(reason_labels)),
        "ui_badge": "Legacy assertion suppressed: not identity evidence" if blocked else "Assertion allowed",
    }


def apply_assertion_scrub_gate(assertion: dict[str, Any]) -> dict[str, Any]:
    gate = assertion_promotion_gate(assertion)
    assertion["legacy_assertion_scrub"] = gate
    assertion["promotion_blocked"] = bool(gate.get("blocked"))
    assertion["promotion_block_reason_labels"] = gate.get("reason_labels", [])

    if gate.get("blocked"):
        assertion["validation_state"] = "suppressed"
        assertion["suppressed_by_scrubber"] = True
        assertion["type"] = gate.get("safe_type") or assertion.get("type")
        payload = assertion.setdefault("payload", {})
        payload["legacy_assertion_scrub"] = gate
        payload["reason_labels"] = gate.get("reason_labels", [])

    return assertion


def apply_assertion_scrub_gates(assertions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [apply_assertion_scrub_gate(item) for item in assertions]


def scrub_summary(assertions: list[dict[str, Any]], observations: list[dict[str, Any]] | None = None, alias_graph: dict[str, Any] | None = None) -> dict[str, Any]:
    blocked_assertions = sum(1 for item in assertions if item.get("legacy_assertion_scrub", {}).get("blocked"))
    blocked_observations = sum(1 for item in observations or [] if item.get("promotion_blocked") or item.get("promotion_gate", {}).get("blocked"))
    blocked_aliases = int(((alias_graph or {}).get("promotion_gates") or {}).get("blocked_alias_count", 0) or 0)

    reason_counts: dict[str, int] = {}
    for item in assertions:
        for reason in item.get("promotion_block_reason_labels") or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    for item in observations or []:
        for reason in item.get("promotion_block_reason_labels") or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    for reason, count in (((alias_graph or {}).get("promotion_gates") or {}).get("reason_counts") or {}).items():
        reason_counts[reason] = reason_counts.get(reason, 0) + int(count or 0)

    return {
        "schema": SCHEMA,
        "blocked_assertion_count": blocked_assertions,
        "blocked_observation_count": blocked_observations,
        "blocked_alias_count": blocked_aliases,
        "blocked_total_count": blocked_assertions + blocked_observations + blocked_aliases,
        "reason_counts": reason_counts,
        "rule": "Legacy asset/CDN profile/url assertions and bogus phone-like assertions are suppressed before dossier use.",
    }


def scrub_legacy_assertions(subject_id: int, actor: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    db.ensure_configured()
    session = db.Session()
    changed: list[dict[str, Any]] = []
    try:
        rows = (
            session.query(db.SpineDossierAssertion)
            .filter_by(subject_id=subject_id)
            .order_by(db.SpineDossierAssertion.id.asc())
            .all()
        )

        for row in rows:
            item = {
                "id": row.id,
                "subject_id": row.subject_id,
                "type": row.assertion_type,
                "value": row.normalized_value,
                "confidence": float(row.confidence or 0),
                "validation_state": row.validation_state,
                "payload": safe_json(row.payload_json, {}),
            }
            gate = assertion_promotion_gate(item)
            if not gate.get("blocked"):
                continue

            changed.append(
                {
                    "assertion_id": row.id,
                    "original_type": row.assertion_type,
                    "safe_type": gate.get("safe_type"),
                    "value": row.normalized_value,
                    "reason_labels": gate.get("reason_labels", []),
                    "previous_state": row.validation_state,
                }
            )

            if dry_run:
                continue

            payload = safe_json(row.payload_json, {})
            payload["legacy_assertion_scrub"] = gate
            payload["reason_labels"] = sorted(set((payload.get("reason_labels") or []) + gate.get("reason_labels", [])))
            payload["scrubbed_by"] = SCHEMA
            payload["scrub_actor"] = actor

            row.assertion_type = gate.get("safe_type") or row.assertion_type
            row.validation_state = "suppressed"
            row.payload_json = json.dumps(payload)
            row.updated_at = db.utc_now()

            session.add(
                db.SpineValidationEvent(
                    assertion_id=row.id,
                    actor=actor,
                    action="suppressed",
                    note="Legacy assertion suppressed: not identity evidence",
                )
            )

        if not dry_run:
            session.commit()

        return {
            "schema": SCHEMA,
            "subject_id": subject_id,
            "dry_run": dry_run,
            "suppressed_count": len(changed),
            "changed": changed,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
