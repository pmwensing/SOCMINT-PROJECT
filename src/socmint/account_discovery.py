from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from . import database as db
from .seeds import normalize_seed

DISCOVERY_TYPES = {"account_presence", "profile_url"}
PROFILE_TYPES = {"profile_url"}


def _json_loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return default


def _platform_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc:
        return parsed.netloc.lower().removeprefix("www.")
    return None


def _assertion_for_observation(observation) -> int | None:
    assertion = db.find_spine_assertion(
        observation.subject_id,
        observation.observation_type,
        observation.normalized_value,
    )
    return assertion.id if assertion else None


def _candidate_from_observation(observation) -> dict[str, Any] | None:
    if observation.observation_type not in DISCOVERY_TYPES:
        return None

    payload = _json_loads(observation.payload_json, {})
    finding = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    context = finding.get("context") if isinstance(finding.get("context"), dict) else {}
    value = str(observation.normalized_value or "").strip()
    if not value:
        return None

    if observation.observation_type in PROFILE_TYPES or value.startswith(
        ("http://", "https://")
    ):
        profile_url = value
        platform = context.get("platform") or context.get("platform_hint")
        platform = platform or _platform_from_url(profile_url)
        account_value = profile_url
    else:
        profile_url = (
            context.get("profile_url") or context.get("url") or finding.get("url")
        )
        platform = value
        account_value = str(context.get("target") or finding.get("target") or value)

    return {
        "subject_id": observation.subject_id,
        "observation_id": observation.id,
        "assertion_id": _assertion_for_observation(observation),
        "discovery_type": observation.observation_type,
        "platform": platform,
        "account_value": account_value,
        "profile_url": profile_url,
        "confidence": float(observation.confidence or 0.5),
        "payload": {
            "source_ref": observation.source_ref,
            "evidence_ref": observation.evidence_ref,
            "observation_payload": payload,
        },
    }


def _capture_profile(candidate: dict[str, Any], actor: str | None = None) -> list[str]:
    profile_url = candidate.get("profile_url")
    if not profile_url:
        return []

    from .high_end_workflows import capture_browser_snapshot

    capture = capture_browser_snapshot(
        profile_url,
        html=(
            "<!doctype html><html><body>"
            f"<h1>Account discovery</h1><p>{profile_url}</p>"
            "</body></html>"
        ),
        subject_id=candidate["subject_id"],
        actor=actor,
        use_playwright=False,
    )
    return [item["capture_id"] for item in capture.get("captures", [])]


def ingest_account_discoveries(
    subject_id: int,
    actor: str | None = None,
    capture_profiles: bool = True,
) -> dict[str, Any]:
    discoveries = []
    created_or_updated = []
    capture_errors = []

    for observation in db.list_spine_observations(subject_id, limit=10000):
        candidate = _candidate_from_observation(observation)
        if not candidate:
            continue
        capture_ids: list[str] = []
        if capture_profiles and candidate.get("profile_url"):
            try:
                capture_ids = _capture_profile(candidate, actor=actor)
            except Exception as exc:
                capture_errors.append(
                    {
                        "observation_id": observation.id,
                        "profile_url": candidate.get("profile_url"),
                        "error": str(exc),
                    }
                )
        row = db.upsert_account_discovery(
            subject_id=candidate["subject_id"],
            observation_id=candidate["observation_id"],
            discovery_type=candidate["discovery_type"],
            account_value=candidate["account_value"],
            platform=candidate.get("platform"),
            profile_url=candidate.get("profile_url"),
            confidence=str(candidate["confidence"]),
            assertion_id=candidate.get("assertion_id"),
            capture_ids=capture_ids,
            payload=candidate["payload"],
            actor=actor,
        )
        item = account_discovery_dict(row)
        discoveries.append(item)
        created_or_updated.append(row.id)

    return {
        "schema": "socmint.account_discovery_ingest.v8_1_0",
        "subject_id": subject_id,
        "discovery_count": len(discoveries),
        "discovery_ids": created_or_updated,
        "capture_errors": capture_errors,
        "discoveries": discoveries,
    }


def account_discovery_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "subject_id": item.subject_id,
        "observation_id": item.observation_id,
        "assertion_id": item.assertion_id,
        "discovery_type": item.discovery_type,
        "platform": item.platform,
        "account_value": item.account_value,
        "profile_url": item.profile_url,
        "confidence": float(item.confidence or 0),
        "review_state": item.review_state,
        "capture_ids": _json_loads(item.capture_ids_json, []),
        "promoted_seed_id": item.promoted_seed_id,
        "payload": _json_loads(item.payload_json, {}),
        "actor": item.actor,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def account_discovery_queue(
    subject_id: int | None = None,
    review_state: str | None = "unreviewed",
    limit: int = 500,
) -> dict[str, Any]:
    items = db.list_account_discoveries(
        subject_id=subject_id,
        review_state=review_state,
        limit=limit,
    )
    return {
        "schema": "socmint.account_discovery_queue.v8_1_0",
        "subject_id": subject_id,
        "review_state": review_state,
        "count": len(items),
        "discoveries": [account_discovery_dict(item) for item in items],
    }


def _seed_for_discovery(item) -> tuple[str, str] | None:
    if item.profile_url:
        return ("url", item.profile_url)
    if item.discovery_type == "account_presence" and "@" not in item.account_value:
        return ("username", item.account_value)
    return None


def review_account_discovery(
    discovery_id: int,
    action: str,
    actor: str | None = None,
    note: str | None = None,
    promote: bool = False,
) -> dict[str, Any]:
    item = db.get_account_discovery(discovery_id)
    if not item:
        raise ValueError("Account discovery not found.")
    if action not in {"confirmed", "rejected", "suppressed", "unreviewed"}:
        raise ValueError("Invalid account discovery review action.")

    promoted_seed_id = None
    if promote and action == "confirmed":
        seed = _seed_for_discovery(item)
        if seed:
            seed_type, raw_value = seed
            normalized = normalize_seed(raw_value, seed_type)
            promoted_seed_id = db.add_spine_seed(
                subject_id=item.subject_id,
                seed_type=normalized.seed_type,
                raw_value=normalized.raw_value,
                normalized_value=normalized.normalized_value,
                pii_hash=normalized.pii_hash,
            )

    updated = db.update_account_discovery_review(
        discovery_id,
        action,
        actor=actor,
        note=note,
        promoted_seed_id=promoted_seed_id,
    )
    if item.assertion_id:
        db.validate_spine_assertion(item.assertion_id, actor, action, note)

    return {
        "schema": "socmint.account_discovery_review.v8_1_0",
        "discovery": account_discovery_dict(updated),
        "promoted_seed_id": promoted_seed_id,
    }
