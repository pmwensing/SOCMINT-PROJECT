from __future__ import annotations

from typing import Any

from . import database
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .human_analytic_review_v30_5 import latest_review

SCHEMA = "socmint.analytic_dossier_contribution.v30_6"
VERSION = "v30.6.0"
ACTION = "analytic_dossier_contribution_reviewed"
DECISIONS = ("approved", "held", "rejected", "withdrawn")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "claim_mutated": False,
        "review_mutated": False,
        "dossier_mutated": False,
    }


def contribution_history() -> list[dict[str, Any]]:
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


def contributions_for_claim(claim_id: str | None = None) -> list[dict[str, Any]]:
    rows = contribution_history()
    return [row for row in rows if row.get("claim_id") == claim_id] if claim_id else rows


def latest_contribution(claim_id: str) -> dict[str, Any] | None:
    rows = contributions_for_claim(claim_id)
    return rows[-1] if rows else None


def current_contribution_decisions() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in contribution_history():
        claim_id = str(item.get("claim_id") or "")
        if not claim_id:
            continue
        histories.setdefault(claim_id, []).append(item)
        latest[claim_id] = dict(item)
    for claim_id, item in latest.items():
        item["contribution_history"] = histories.get(claim_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("claim_id")))


def _record(actor: str, claim_id: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
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


def review_dossier_contribution(
    *,
    actor: str,
    claim_id: str,
    decision: str,
    target_section: str,
    rationale: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    claim = find_claim(claim_id)
    decision = str(decision or "").strip()
    target_section = str(target_section or "").strip()
    rationale = str(rationale or "").strip()
    reason = str(reason or "").strip()

    if claim is None:
        return blocked("corroboration_claim_required")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")
    if confirmed is not True:
        return blocked("explicit_dossier_contribution_confirmation_required")
    if decision not in DECISIONS:
        return blocked("dossier_contribution_decision_invalid")
    if decision != "withdrawn" and not target_section:
        return blocked("dossier_target_section_required")
    if not rationale:
        return blocked("dossier_contribution_rationale_required")
    if not reason:
        return blocked("administrative_reason_required")

    human_review = latest_review(claim_id)
    if human_review is None:
        return blocked("human_analytic_review_required")
    prior = latest_contribution(claim_id)

    if decision == "approved":
        if human_review.get("decision") != "approved":
            return blocked("approved_human_review_required")
        if human_review.get("consequential_use_authorized") is not True:
            return blocked("consequential_use_authorization_required")
    if decision == "withdrawn":
        if prior is None or prior.get("decision") != "approved":
            return blocked("approved_contribution_required_for_withdrawal")

    binding = {
        "claim_id": claim_id,
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "human_review_id": human_review.get("human_review_id"),
        "human_review_sha256": human_review.get("human_review_sha256"),
        "human_review_decision": human_review.get("decision"),
        "supersedes_contribution_id": prior.get("dossier_contribution_id") if prior else None,
    }
    content = {
        "event_type": ACTION,
        "claim_id": claim_id,
        "case_id": claim.get("case_id"),
        "entity_id": claim.get("entity_id"),
        "decision": decision,
        "target_section": target_section or None,
        "rationale": rationale,
        "contribution_binding": binding,
        "contribution_binding_sha256": _sha(binding),
        "reason": reason,
        "is_reassessment": prior is not None,
        "supersedes_contribution_id": prior.get("dossier_contribution_id") if prior else None,
        "dossier_contribution_authorized": decision == "approved",
        "dossier_mutation_performed": False,
        "claim_mutated": False,
        "review_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "dossier_contribution_id": f"dossier-contribution-{digest[:24]}",
        "dossier_contribution_sha256": digest,
    }
    if any(item.get("dossier_contribution_sha256") == digest for item in contributions_for_claim(claim_id)):
        return blocked("dossier_contribution_record_already_exists")

    result = _record(actor, claim_id, event, ip_address)
    return {
        **result,
        "status": "analytic_dossier_contribution_reviewed",
        "next_action": "contribute_through_existing_dossier_pipeline" if decision == "approved" else "retain_contribution_history",
    }
