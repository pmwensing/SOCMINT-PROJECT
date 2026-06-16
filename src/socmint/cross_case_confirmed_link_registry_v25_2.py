from __future__ import annotations

from collections import Counter
from typing import Any

from . import database
from .cross_case_correlation_review_v25_1 import (
    ACTION as REVIEW_ACTION,
    correlation_review_history,
    latest_correlation_review,
)
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.cross_case_confirmed_link_registry.v25_2"
VERSION = "v25.2.0"
ACTION = "cross_case_confirmed_link_registered"


def _blocked(correlation_id: str, key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "correlation_id": correlation_id,
        "status": "blocked",
        "blockers": [{"key": key}],
        "source_records_mutated": False,
        "review_history_mutated": False,
        "candidate_mutated": False,
    }


def _existing_for_review(review_decision_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action == ACTION)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .all()
        )
        for row in rows:
            details = _json_details(row)
            if details.get("accepted_review_decision_id") == review_decision_id:
                return {
                    **details,
                    "registry_record_id": row.id,
                    "registered_at": row.created_at.isoformat() if row.created_at else None,
                    "registered_by": row.actor,
                }
        return None
    finally:
        session.close()


def register_confirmed_cross_case_link(
    correlation_id: str,
    *,
    registered_by: str,
    confirmed: bool,
    allowed_case_ids: set[str] | None = None,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return _blocked(correlation_id, "explicit_confirmed_link_registration_required")

    actor = str(registered_by or "").strip()
    if not actor:
        return _blocked(correlation_id, "confirmed_link_registrar_identity_required")

    review = latest_correlation_review(correlation_id)
    if review is None:
        return _blocked(correlation_id, "accepted_correlation_review_required")
    if review.get("decision") != "accept":
        return _blocked(correlation_id, "latest_correlation_review_must_be_accept")

    review_decision_id = str(review.get("review_decision_id") or "").strip()
    review_decision_sha256 = str(review.get("review_decision_sha256") or "").strip()
    if not review_decision_id or not review_decision_sha256:
        return _blocked(correlation_id, "accepted_review_binding_incomplete")

    candidate = review.get("candidate_snapshot") or {}
    occurrences = list(candidate.get("occurrences") or [])
    case_ids = sorted({str(value) for value in candidate.get("case_ids") or [] if str(value)})
    if not occurrences or len(case_ids) < 2:
        return _blocked(correlation_id, "accepted_review_source_occurrences_required")
    if allowed_case_ids is not None and any(case_id not in allowed_case_ids for case_id in case_ids):
        return _blocked(correlation_id, "confirmed_link_case_access_required")

    existing = _existing_for_review(review_decision_id)
    if existing is not None:
        return {
            **existing,
            "status": "confirmed_link_already_registered",
            "duplicate": True,
        }

    occurrence_snapshot = sorted(
        occurrences,
        key=lambda value: (
            value.get("occurred_at") or "",
            int(value.get("record_id") or 0),
            value.get("field_path") or "",
        ),
    )
    occurrence_snapshot_sha256 = _sha(occurrence_snapshot)
    accepted_review_snapshot = {
        "review_decision_id": review_decision_id,
        "review_decision_sha256": review_decision_sha256,
        "action_record_id": review.get("action_record_id"),
        "recorded_at": review.get("recorded_at"),
        "reviewer": review.get("reviewer"),
        "reason": review.get("reason"),
        "candidate_sha256": review.get("candidate_sha256"),
        "workspace_access_scope": review.get("workspace_access_scope"),
    }
    content = {
        "correlation_id": correlation_id,
        "category": candidate.get("category"),
        "match_value": candidate.get("match_value"),
        "display_values": candidate.get("display_values"),
        "case_ids": case_ids,
        "case_count": len(case_ids),
        "source_occurrences": occurrence_snapshot,
        "source_occurrence_count": len(occurrence_snapshot),
        "source_occurrences_sha256": occurrence_snapshot_sha256,
        "accepted_review": accepted_review_snapshot,
        "accepted_review_decision_id": review_decision_id,
        "accepted_review_decision_sha256": review_decision_sha256,
        "note": str(note or "").strip(),
    }
    link_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "confirmed_link_id": f"confirmed-cross-case-link-{link_sha256[:24]}",
        "confirmed_link_sha256": link_sha256,
        "link_status": "confirmed",
        "source_occurrences_preserved": True,
        "source_records_mutated": False,
        "review_history_mutated": False,
        "candidate_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=correlation_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        registered_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "confirmed_link_registered",
        "registry_record_id": record_id,
        "registered_at": registered_at,
        "registered_by": actor,
        "duplicate": False,
    }


def confirmed_link_registry(
    *, allowed_case_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action == ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        links = []
        for row in rows:
            details = _json_details(row)
            case_ids = {str(value) for value in details.get("case_ids") or []}
            if allowed_case_ids is not None and any(case_id not in allowed_case_ids for case_id in case_ids):
                continue
            links.append({
                **details,
                "registry_record_id": row.id,
                "registered_at": row.created_at.isoformat() if row.created_at else None,
                "registered_by": row.actor,
            })
        return links
    finally:
        session.close()


def _all_review_histories() -> dict[str, list[dict[str, Any]]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action == REVIEW_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        correlation_ids = sorted({str(row.target_value) for row in rows if row.target_value})
    finally:
        session.close()
    return {correlation_id: correlation_review_history(correlation_id) for correlation_id in correlation_ids}


def build_confirmed_link_registry_workspace(
    *, allowed_case_ids: set[str] | None = None
) -> dict[str, Any]:
    links = confirmed_link_registry(allowed_case_ids=allowed_case_ids)
    review_histories = _all_review_histories()
    disposition_counts: Counter[str] = Counter()
    accepted_pending = []
    registered_review_ids = {link.get("accepted_review_decision_id") for link in links}

    for correlation_id, history in review_histories.items():
        if not history:
            continue
        for review in history:
            disposition_counts[str(review.get("decision") or "unknown")] += 1
        latest = history[-1]
        candidate = latest.get("candidate_snapshot") or {}
        case_ids = {str(value) for value in candidate.get("case_ids") or []}
        if allowed_case_ids is not None and any(case_id not in allowed_case_ids for case_id in case_ids):
            continue
        if latest.get("decision") == "accept" and latest.get("review_decision_id") not in registered_review_ids:
            accepted_pending.append({
                "correlation_id": correlation_id,
                "review_decision_id": latest.get("review_decision_id"),
                "review_decision_sha256": latest.get("review_decision_sha256"),
                "reviewer": latest.get("reviewer"),
                "reason": latest.get("reason"),
                "case_ids": sorted(case_ids),
                "category": candidate.get("category"),
                "match_value": candidate.get("match_value"),
            })

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "access_scope": {
            "mode": "restricted" if allowed_case_ids is not None else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None,
        },
        "confirmed_links": links,
        "confirmed_link_count": len(links),
        "accepted_pending_registration": sorted(
            accepted_pending, key=lambda item: (item["correlation_id"], item.get("review_decision_id") or "")
        ),
        "accepted_pending_count": len(accepted_pending),
        "review_disposition_counts": dict(sorted(disposition_counts.items())),
        "review_histories": review_histories,
        "unreviewed_candidates_materialized": False,
        "rejected_deferred_split_history_retained": True,
        "source_records_mutated": False,
        "registry_record_created_by_view": False,
        "next_action": (
            "register_accepted_cross_case_links"
            if accepted_pending
            else "review_confirmed_cross_case_links"
        ),
    }
