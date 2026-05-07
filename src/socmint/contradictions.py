import json
from collections import defaultdict

from . import database as db


SINGLE_VALUE_ASSERTION_TYPES = {
    "profile_display_name",
    "profile_username",
    "profile_bio",
    "profile_avatar_url",
    "profile_platform",
    "phone",
    "email",
}


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def detect_subject_contradictions(subject_id: int) -> dict:
    if not db.get_spine_subject(subject_id):
        raise ValueError("Subject not found.")

    db.clear_spine_contradictions(subject_id)
    assertions = db.list_spine_assertions(subject_id)
    created = []

    created.extend(detect_single_value_conflicts(subject_id, assertions))
    created.extend(detect_validation_conflicts(subject_id, assertions))
    created.extend(detect_confidence_conflicts(subject_id, assertions))

    return {"subject_id": subject_id, "contradiction_ids": created}


def detect_single_value_conflicts(subject_id, assertions):
    created = []
    grouped = defaultdict(list)

    for assertion in assertions:
        if assertion.assertion_type in SINGLE_VALUE_ASSERTION_TYPES:
            grouped[assertion.assertion_type].append(assertion)

    for assertion_type, items in grouped.items():
        values = {
            (item.normalized_value or "").strip().lower()
            for item in items
            if item.normalized_value
        }
        if len(values) < 2:
            continue

        severity = "high" if assertion_type in {"email", "phone"} else "medium"
        payload = {
            "assertion_type": assertion_type,
            "conflicting_values": sorted(values),
            "assertion_ids": [item.id for item in items],
            "reason": "Multiple values found for a single-value attribute.",
        }
        created.append(
            db.create_spine_contradiction(
                subject_id=subject_id,
                conflict_type="single_value_conflict",
                severity=severity,
                status="open",
                assertion_ids=[item.id for item in items],
                summary=(
                    f"{assertion_type} has {len(values)} conflicting values."
                ),
                payload=payload,
            )
        )

    return created


def detect_validation_conflicts(subject_id, assertions):
    created = []
    grouped = defaultdict(list)

    for assertion in assertions:
        key = (
            assertion.assertion_type,
            (assertion.normalized_value or "").strip().lower(),
        )
        grouped[key].append(assertion)

    for (assertion_type, value), items in grouped.items():
        states = {item.validation_state for item in items}
        if "confirmed" not in states or "rejected" not in states:
            continue

        payload = {
            "assertion_type": assertion_type,
            "value": value,
            "states": sorted(states),
            "assertion_ids": [item.id for item in items],
            "reason": "Same assertion value has conflicting validation states.",
        }
        created.append(
            db.create_spine_contradiction(
                subject_id=subject_id,
                conflict_type="validation_conflict",
                severity="high",
                status="open",
                assertion_ids=[item.id for item in items],
                summary=f"{assertion_type}={value} has conflicting review states.",
                payload=payload,
            )
        )

    return created


def detect_confidence_conflicts(subject_id, assertions):
    created = []
    grouped = defaultdict(list)

    for assertion in assertions:
        grouped[assertion.assertion_type].append(assertion)

    for assertion_type, items in grouped.items():
        if len(items) < 2:
            continue

        scores = [float(item.confidence or 0) for item in items]
        high = max(scores)
        low = min(scores)

        if high < 0.8 or low > 0.45:
            continue

        payload = {
            "assertion_type": assertion_type,
            "high_confidence": high,
            "low_confidence": low,
            "assertion_ids": [item.id for item in items],
            "reason": "Same assertion class has both strong and weak claims.",
        }
        created.append(
            db.create_spine_contradiction(
                subject_id=subject_id,
                conflict_type="confidence_gap",
                severity="low",
                status="open",
                assertion_ids=[item.id for item in items],
                summary=(
                    f"{assertion_type} has a large confidence spread "
                    f"({low:.3f} to {high:.3f})."
                ),
                payload=payload,
            )
        )

    return created


def contradiction_payload(subject_id: int) -> dict:
    contradictions = db.list_spine_contradictions(subject_id)
    return {
        "subject_id": subject_id,
        "contradictions": [
            {
                "id": item.id,
                "type": item.conflict_type,
                "severity": item.severity,
                "status": item.status,
                "summary": item.summary,
                "assertion_ids": _json_loads(item.assertion_ids_json, []),
                "payload": _json_loads(item.payload_json),
                "created_at": item.created_at.isoformat()
                if item.created_at
                else None,
                "updated_at": item.updated_at.isoformat()
                if item.updated_at
                else None,
            }
            for item in contradictions
        ],
    }


def resolve_contradiction(contradiction_id, status, actor=None, note=None):
    if status not in {"open", "resolved", "ignored", "needs_review"}:
        raise ValueError("Invalid contradiction status.")
    return db.update_spine_contradiction(
        contradiction_id,
        status=status,
        actor=actor,
        note=note,
    )
