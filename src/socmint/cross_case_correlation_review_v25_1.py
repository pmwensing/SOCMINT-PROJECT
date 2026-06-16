from __future__ import annotations

from typing import Any

from . import database
from .cross_case_intelligence_workspace_v25_0 import (
    build_cross_case_intelligence_workspace,
)
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.cross_case_correlation_review.v25_1"
VERSION = "v25.1.0"
ACTION = "cross_case_correlation_candidate_review"
DECISIONS = {"accept", "reject", "defer", "split"}
CATEGORY_KEYS = {
    "entity": "entities",
    "identifier": "identifiers",
    "infrastructure": "infrastructure",
    "evidence": "evidence",
    "timeline": "timelines",
}


def _candidate_from_workspace(
    correlation_id: str,
    category: str,
    *,
    allowed_case_ids: set[str] | None,
    minimum_case_count: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    workspace = build_cross_case_intelligence_workspace(
        allowed_case_ids=allowed_case_ids,
        minimum_case_count=minimum_case_count,
    )
    key = CATEGORY_KEYS.get(category)
    if key is None:
        return None, workspace
    candidate = next(
        (
            item
            for item in workspace.get("correlations", {}).get(key, [])
            if item.get("correlation_id") == correlation_id
        ),
        None,
    )
    return candidate, workspace


def _blocked(correlation_id: str, key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "correlation_id": correlation_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "candidate_mutated": False,
    }


def _normalize_split_groups(
    groups: Any,
    occurrences: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if not isinstance(groups, list) or len(groups) < 2:
        return None
    valid_hashes = {str(item.get("provenance_sha256")) for item in occurrences}
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        if not isinstance(group, dict):
            return None
        hashes = group.get("occurrence_provenance_sha256")
        if not isinstance(hashes, list) or not hashes:
            return None
        clean = [str(value).strip() for value in hashes if str(value).strip()]
        if len(clean) != len(set(clean)):
            return None
        if any(value not in valid_hashes or value in seen for value in clean):
            return None
        seen.update(clean)
        normalized.append({
            "group_id": str(group.get("group_id") or f"group-{index}"),
            "label": str(group.get("label") or "").strip(),
            "occurrence_provenance_sha256": sorted(clean),
        })
    if seen != valid_hashes:
        return None
    return normalized


def review_correlation_candidate(
    correlation_id: str,
    *,
    category: str,
    decision: str,
    reason: str,
    reviewer: str,
    confirmed: bool,
    split_groups: Any = None,
    allowed_case_ids: set[str] | None = None,
    minimum_case_count: int = 2,
    ip_address: str | None = None,
) -> dict[str, Any]:
    decision_value = str(decision or "").strip().lower()
    category_value = str(category or "").strip().lower()
    reason_value = str(reason or "").strip()
    reviewer_value = str(reviewer or "").strip()

    if confirmed is not True:
        return _blocked(correlation_id, "explicit_correlation_review_confirmation_required")
    if decision_value not in DECISIONS:
        return _blocked(correlation_id, "correlation_review_decision_invalid")
    if not reviewer_value:
        return _blocked(correlation_id, "correlation_reviewer_identity_required")
    if not reason_value:
        return _blocked(correlation_id, "correlation_review_reason_required")

    candidate, workspace = _candidate_from_workspace(
        correlation_id,
        category_value,
        allowed_case_ids=allowed_case_ids,
        minimum_case_count=minimum_case_count,
    )
    if candidate is None:
        return _blocked(correlation_id, "visible_correlation_candidate_required")

    candidate_snapshot = {
        "correlation_id": candidate.get("correlation_id"),
        "category": candidate.get("category"),
        "match_value": candidate.get("match_value"),
        "display_values": candidate.get("display_values"),
        "case_ids": candidate.get("case_ids"),
        "case_count": candidate.get("case_count"),
        "occurrence_count": candidate.get("occurrence_count"),
        "occurrences": candidate.get("occurrences"),
        "human_review_required": candidate.get("human_review_required"),
        "confirmed_match": candidate.get("confirmed_match"),
    }
    candidate_sha256 = _sha(candidate_snapshot)

    normalized_groups = None
    if decision_value == "split":
        normalized_groups = _normalize_split_groups(
            split_groups,
            list(candidate_snapshot.get("occurrences") or []),
        )
        if normalized_groups is None:
            return _blocked(correlation_id, "valid_complete_split_groups_required")

    content = {
        "correlation_id": correlation_id,
        "category": category_value,
        "decision": decision_value,
        "reason": reason_value,
        "reviewer": reviewer_value,
        "candidate_snapshot": candidate_snapshot,
        "candidate_sha256": candidate_sha256,
        "workspace_access_scope": workspace.get("access_scope"),
        "workspace_minimum_case_count": workspace.get("minimum_case_count"),
        "split_groups": normalized_groups,
    }
    decision_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "review_decision_id": f"correlation-review-{decision_sha256[:24]}",
        "review_decision_sha256": decision_sha256,
        "source_occurrence_count": len(candidate_snapshot.get("occurrences") or []),
        "source_occurrences_preserved": True,
        "source_records_mutated": False,
        "candidate_mutated": False,
        "case_provenance_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=reviewer_value,
            action=ACTION,
            target_value=correlation_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        recorded_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "correlation_review_recorded",
        "action_record_id": record_id,
        "recorded_at": recorded_at,
    }


def correlation_review_history(correlation_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(
                database.AuditLog.action == ACTION,
                database.AuditLog.target_value == correlation_id,
            )
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "action_record_id": row.id,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def latest_correlation_review(correlation_id: str) -> dict[str, Any] | None:
    history = correlation_review_history(correlation_id)
    return history[-1] if history else None
