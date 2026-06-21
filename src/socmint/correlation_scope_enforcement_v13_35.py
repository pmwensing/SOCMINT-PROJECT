from __future__ import annotations

import hashlib
import re
from typing import Any

SCHEMA = "socmint.correlation_scope_enforcement.v13_35B"
VERSION = "v13.35B"

AMBIGUOUS_PROFILE_TYPES = {
    "profile",
    "profile_url",
    "profile_name",
    "profile_display_name",
    "social_profile",
    "social_media_profile",
    "account",
    "handle",
}


def normalize_target_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def compact_target_value(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_target_value(value))


def derive_correlation_scope_id(
    *,
    subject_id: Any = None,
    seed_id: Any = None,
    connector_run_id: Any = None,
    target_type: Any = None,
    target_value: Any = None,
    legacy: bool = True,
) -> str:
    parts = [
        "legacy" if legacy else "scope",
        f"subject:{subject_id or 'unknown'}",
        f"seed:{seed_id or 'unknown'}",
        f"run:{connector_run_id or 'unknown'}",
        f"type:{normalize_target_value(target_type) or 'unknown'}",
        f"value:{compact_target_value(target_value) or 'unknown'}",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"cs_{digest}"


def deterministic_same_target(
    *,
    left_type: Any = None,
    left_value: Any = None,
    right_type: Any = None,
    right_value: Any = None,
) -> dict[str, Any]:
    left_type_n = normalize_target_value(left_type)
    right_type_n = normalize_target_value(right_type)
    left_value_n = normalize_target_value(left_value)
    right_value_n = normalize_target_value(right_value)

    reasons = []
    if left_type_n and right_type_n and left_type_n == right_type_n:
        if left_value_n and right_value_n and left_value_n == right_value_n:
            reasons.append("same_type_exact_normalized_value")
        if compact_target_value(left_value_n) and compact_target_value(
            left_value_n
        ) == compact_target_value(right_value_n):
            reasons.append("same_type_exact_compact_value")

    return {"same_target": bool(reasons), "reasons": sorted(set(reasons))}


def promotion_scope_decision(
    *,
    finding_scope_id: str | None,
    parent_scope_id: str | None,
    finding_type: Any = None,
    finding_value: Any = None,
    parent_type: Any = None,
    parent_value: Any = None,
    analyst_merged_scope: bool = False,
) -> dict[str, Any]:
    same_scope = bool(
        finding_scope_id and parent_scope_id and finding_scope_id == parent_scope_id
    )
    same_target = deterministic_same_target(
        left_type=finding_type,
        left_value=finding_value,
        right_type=parent_type,
        right_value=parent_value,
    )
    ambiguous = normalize_target_value(finding_type) in AMBIGUOUS_PROFILE_TYPES

    if same_scope:
        state, reason = "allow", "same_correlation_scope"
    elif analyst_merged_scope:
        state, reason = "allow", "analyst_merged_scope"
    elif same_target["same_target"]:
        state, reason = "allow", "deterministic_same_target"
    elif ambiguous:
        state, reason = "quarantine", "ambiguous_cross_scope_profile"
    else:
        state, reason = "needs_review", "cross_scope_without_same_target_proof"

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "state": state,
        "reason": reason,
        "same_scope": same_scope,
        "analyst_merged_scope": analyst_merged_scope,
        "same_target": same_target,
        "finding_scope_id": finding_scope_id,
        "parent_scope_id": parent_scope_id,
        "finding_type": normalize_target_value(finding_type),
        "parent_type": normalize_target_value(parent_type),
    }


def should_promote(decision: dict[str, Any]) -> bool:
    return decision.get("state") == "allow"


def should_quarantine(decision: dict[str, Any]) -> bool:
    return decision.get("state") == "quarantine"
