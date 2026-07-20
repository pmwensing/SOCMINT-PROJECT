from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .source_registry_v36_1 import find_source

SCHEMA = "socmint.source_independence.v36_4"
VERSION = "v36.4.0"
ACTION = "source_independence_assessed"
RELATIONSHIPS = (
    "independent",
    "mirror",
    "syndication",
    "derivative",
    "common_origin",
    "unknown",
)
SIGNAL_TYPES = frozenset(
    {
        "exact_content_hash",
        "canonical_url_match",
        "explicit_syndication",
        "common_outbound_citation",
        "archive_ancestry",
        "shared_registry_record",
        "identical_structured_metadata",
        "quoted_passage_overlap",
        "independent_primary_capture",
    }
)
DEPENDENCY_SIGNALS = SIGNAL_TYPES - {"independent_primary_capture"}
INDEPENDENCE_SCORES = {
    "independent": 100,
    "common_origin": 20,
    "derivative": 10,
    "syndication": 5,
    "mirror": 0,
    "unknown": 0,
}


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_mutated": False,
        "truth_assigned": False,
        "claim_approved": False,
        "dossier_mutated": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
            .order_by(
                database.AuditLog.created_at.asc(),
                database.AuditLog.id.asc(),
            )
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    actor: str,
    group_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=group_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "recorded_at": (
                row.created_at.isoformat() if row.created_at else None
            ),
        }
    finally:
        session.close()


def current_independence_assessments() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        group_id = str(event.get("independence_group_id") or "")
        if group_id:
            current[group_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("independence_group_id") or ""),
    )


def find_independence_group(group_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_independence_assessments()
            if item.get("independence_group_id") == group_id
        ),
        None,
    )


def groups_for_sources(source_ids: list[str]) -> list[dict[str, Any]]:
    wanted = set(source_ids)
    return [
        item
        for item in current_independence_assessments()
        if wanted.intersection(item.get("source_ids") or [])
    ]


def _normalize_signals(signals: Any) -> tuple[list[dict[str, str]], str | None]:
    if not isinstance(signals, list) or not signals:
        return [], "source_independence_signals_required"
    normalized = []
    for item in signals:
        if not isinstance(item, dict):
            return [], "source_independence_signal_invalid"
        signal_type = _required(item.get("signal_type"))
        reason = _required(item.get("reason"))
        if signal_type not in SIGNAL_TYPES or not reason:
            return [], "source_independence_signal_invalid"
        normalized.append({"signal_type": signal_type, "reason": reason})
    normalized.sort(key=lambda item: (item["signal_type"], item["reason"]))
    return normalized, None


def assess_source_independence(
    *,
    actor: str,
    case_id: str,
    source_ids: list[str] | None,
    relationship: str,
    signals: list[dict[str, Any]] | None,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    relationship = _required(relationship)
    reason = _required(reason)
    normalized_ids = sorted(
        {
            _required(source_id)
            for source_id in (source_ids or [])
            if _required(source_id)
        }
    )
    normalized_limitations = sorted(
        {
            _required(item)
            for item in (limitations or [])
            if _required(item)
        }
    )
    if confirmed is not True:
        return blocked("explicit_source_independence_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id:
        return blocked("case_id_required")
    if len(normalized_ids) < 2:
        return blocked("at_least_two_sources_required")
    if relationship not in RELATIONSHIPS:
        return blocked("source_relationship_invalid")
    if not reason:
        return blocked("administrative_reason_required")

    normalized_signals, error = _normalize_signals(signals)
    if error:
        return blocked(error)
    signal_types = {item["signal_type"] for item in normalized_signals}
    sources = []
    for source_id in normalized_ids:
        source = find_source(source_id)
        if source is None:
            return blocked("source_record_required")
        if str(source.get("case_id") or "") != case_id:
            return blocked("source_independence_case_mismatch")
        sources.append(source)

    content_hashes = {
        str((source.get("capture") or {}).get("content_sha256") or "")
        for source in sources
    }
    content_hashes.discard("")
    exact_hash_match = len(content_hashes) == 1 and len(sources) > 1
    if exact_hash_match:
        signal_types.add("exact_content_hash")
        normalized_signals = sorted(
            [
                *normalized_signals,
                {
                    "signal_type": "exact_content_hash",
                    "reason": "Registered captures have the same content SHA-256.",
                },
            ],
            key=lambda item: (item["signal_type"], item["reason"]),
        )
    if relationship == "independent":
        if exact_hash_match or signal_types.intersection(DEPENDENCY_SIGNALS):
            return blocked("independent_relationship_conflicts_with_dependency_evidence")
        if "independent_primary_capture" not in signal_types:
            return blocked("independent_primary_capture_signal_required")
    if relationship == "mirror" and not signal_types.intersection(
        {"exact_content_hash", "canonical_url_match"}
    ):
        return blocked("mirror_relationship_requires_matching_signal")

    source_bindings = [
        {
            "source_id": source.get("source_id"),
            "source_event_sha256": source.get("source_event_sha256"),
            "capture_sha256": source.get("capture_sha256"),
            "content_sha256": (source.get("capture") or {}).get(
                "content_sha256"
            ),
            "canonical_url": (source.get("capture") or {}).get(
                "canonical_url"
            ),
        }
        for source in sources
    ]
    group_identity = {"case_id": case_id, "source_ids": normalized_ids}
    group_id = f"source-independence-group-{_sha(group_identity)[:24]}"
    content = {
        "event_type": ACTION,
        "independence_group_id": group_id,
        "case_id": case_id,
        "source_ids": normalized_ids,
        "source_bindings": source_bindings,
        "source_bindings_sha256": _sha(source_bindings),
        "relationship": relationship,
        "independence_score": INDEPENDENCE_SCORES[relationship],
        "signals": normalized_signals,
        "signals_sha256": _sha(normalized_signals),
        "limitations": normalized_limitations,
        "reason": reason,
        "source_mutated": False,
        "truth_assigned": False,
        "claim_approved": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    assessment_id = f"source-independence-assessment-{digest[:24]}"
    if any(
        item.get("source_independence_assessment_id") == assessment_id
        for item in _history()
    ):
        return blocked("source_independence_assessment_already_exists")
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "source_independence_assessment_id": assessment_id,
        "source_independence_assessment_sha256": digest,
    }
    result = _record(actor, group_id, event, ip_address)
    return {
        **result,
        "status": "source_independence_assessed",
        "next_action": "use_independence_group_for_claim_verification",
    }
