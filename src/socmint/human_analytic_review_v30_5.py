from __future__ import annotations

from typing import Any

from . import database
from .analytic_confidence_v30_4 import latest_confidence
from .analytic_conflict_v30_3 import current_conflicts
from .claim_source_linkage_v30_2 import claim_linkages
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.human_analytic_review.v30_5"
VERSION = "v30.5.0"
ACTION = "human_analytic_review_recorded"
DECISIONS = ("approved", "held", "rejected", "needs_revision")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "claim_mutated": False,
        "confidence_mutated": False,
        "dossier_mutated": False,
    }


def review_history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def reviews_for_claim(claim_id: str | None = None) -> list[dict[str, Any]]:
    rows = review_history()
    return (
        [row for row in rows if row.get("claim_id") == claim_id] if claim_id else rows
    )


def latest_review(claim_id: str) -> dict[str, Any] | None:
    rows = reviews_for_claim(claim_id)
    return rows[-1] if rows else None


def current_review_decisions() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in review_history():
        claim_id = str(item.get("claim_id") or "")
        if not claim_id:
            continue
        histories.setdefault(claim_id, []).append(item)
        latest[claim_id] = dict(item)
    for claim_id, item in latest.items():
        item["review_history"] = histories.get(claim_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("claim_id")))


def _record(
    actor: str, claim_id: str, event: dict[str, Any], ip_address: str | None
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=claim_id,
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
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_human_review(
    *,
    actor: str,
    claim_id: str,
    decision: str,
    rationale: str,
    findings: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    claim = find_claim(claim_id)
    decision = str(decision or "").strip()
    rationale = str(rationale or "").strip()
    reason = str(reason or "").strip()
    findings = sorted(
        {str(item).strip() for item in (findings or []) if str(item).strip()}
    )

    if claim is None:
        return blocked("corroboration_claim_required")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")
    if confirmed is not True:
        return blocked("explicit_human_review_confirmation_required")
    if decision not in DECISIONS:
        return blocked("human_review_decision_invalid")
    if not rationale:
        return blocked("review_rationale_required")
    if not reason:
        return blocked("administrative_reason_required")

    confidence = latest_confidence(claim_id)
    if confidence is None:
        return blocked("analytic_confidence_assessment_required")
    linkages = claim_linkages(claim_id)
    if not linkages:
        return blocked("claim_source_linkage_required")
    conflicts = [
        item
        for item in current_conflicts()
        if claim_id in {item.get("claim_a_id"), item.get("claim_b_id")}
    ]
    unresolved = [item for item in conflicts if item.get("resolution") == "unresolved"]

    if decision == "approved":
        if confidence.get("confidence_band") != "substantial":
            return blocked("substantial_confidence_required_for_approval")
        if unresolved:
            return blocked("unresolved_analytic_conflict_blocks_approval")

    prior = latest_review(claim_id)
    binding = {
        "claim_id": claim_id,
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "confidence_assessment_id": confidence.get("confidence_assessment_id"),
        "confidence_assessment_sha256": confidence.get("confidence_assessment_sha256"),
        "source_linkage_sha256": [item.get("linkage_sha256") for item in linkages],
        "conflict_state": [
            {
                "conflict_id": item.get("conflict_id"),
                "resolution": item.get("resolution"),
                "conflict_event_sha256": item.get("conflict_event_sha256"),
                "resolution_event_sha256": item.get("resolution_event_sha256"),
            }
            for item in conflicts
        ],
        "supersedes_review_id": prior.get("human_review_id") if prior else None,
    }
    content = {
        "event_type": ACTION,
        "claim_id": claim_id,
        "case_id": claim.get("case_id"),
        "entity_id": claim.get("entity_id"),
        "decision": decision,
        "rationale": rationale,
        "findings": findings,
        "review_binding": binding,
        "review_binding_sha256": _sha(binding),
        "reason": reason,
        "is_reassessment": prior is not None,
        "supersedes_review_id": prior.get("human_review_id") if prior else None,
        "human_review_complete": True,
        "consequential_use_authorized": decision == "approved",
        "dossier_contribution_authorized": False,
        "claim_mutated": False,
        "confidence_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "human_review_id": f"human-review-{digest[:24]}",
        "human_review_sha256": digest,
    }
    if any(
        item.get("human_review_sha256") == digest
        for item in reviews_for_claim(claim_id)
    ):
        return blocked("human_review_record_already_exists")

    result = _record(actor, claim_id, event, ip_address)
    return {
        **result,
        "status": "human_analytic_review_recorded",
        "next_action": "evaluate_dossier_contribution_and_reassessment",
    }
