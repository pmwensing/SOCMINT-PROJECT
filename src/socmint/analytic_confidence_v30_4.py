from __future__ import annotations

from typing import Any

from . import database
from .analytic_conflict_v30_3 import current_conflicts
from .claim_source_linkage_v30_2 import claim_linkages
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.analytic_confidence.v30_4"
VERSION = "v30.4.0"
ACTION = "analytic_confidence_assessed"
BANDS = ("insufficient", "limited", "moderate", "substantial")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "truth_assigned": False,
        "high_confidence_assigned": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }


def confidence_history() -> list[dict[str, Any]]:
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


def confidence_assessments(claim_id: str | None = None) -> list[dict[str, Any]]:
    rows = confidence_history()
    return (
        [row for row in rows if row.get("claim_id") == claim_id] if claim_id else rows
    )


def latest_confidence(claim_id: str) -> dict[str, Any] | None:
    rows = confidence_assessments(claim_id)
    return rows[-1] if rows else None


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


def _score(
    linkages: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    limitations: list[str],
) -> tuple[int, list[dict[str, Any]]]:
    artifact_ids: set[str] = set()
    observation_ids: set[str] = set()
    for linkage in linkages:
        manifest = linkage.get("source_manifest") or {}
        artifact_ids.update(
            str(item.get("artifact_id"))
            for item in manifest.get("artifact_bindings") or []
            if item.get("artifact_id")
        )
        observation_ids.update(
            str(item.get("observation_id"))
            for item in manifest.get("observation_bindings") or []
            if item.get("observation_id")
        )
    unresolved = [item for item in conflicts if item.get("resolution") == "unresolved"]
    resolved = [item for item in conflicts if item.get("resolution") != "unresolved"]
    components = [
        {
            "key": "source_linkage_present",
            "points": 20 if linkages else 0,
            "detail": len(linkages),
        },
        {
            "key": "accepted_artifact_diversity",
            "points": min(25, len(artifact_ids) * 10),
            "detail": len(artifact_ids),
        },
        {
            "key": "observation_support",
            "points": min(25, len(observation_ids) * 8),
            "detail": len(observation_ids),
        },
        {
            "key": "resolved_conflict_context",
            "points": min(10, len(resolved) * 5),
            "detail": len(resolved),
        },
        {
            "key": "unresolved_conflict_penalty",
            "points": -min(30, len(unresolved) * 15),
            "detail": len(unresolved),
        },
        {
            "key": "declared_limitation_penalty",
            "points": -min(20, len(limitations) * 5),
            "detail": len(limitations),
        },
    ]
    score = max(0, min(79, sum(int(item["points"]) for item in components)))
    return score, components


def assess_confidence(
    *,
    actor: str,
    claim_id: str,
    methodology: str,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    claim = find_claim(claim_id)
    methodology = str(methodology or "").strip()
    reason = str(reason or "").strip()
    limitations = sorted(
        {str(item).strip() for item in (limitations or []) if str(item).strip()}
    )
    if claim is None:
        return blocked("corroboration_claim_required")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")
    if confirmed is not True:
        return blocked("explicit_confidence_assessment_confirmation_required")
    if not methodology:
        return blocked("confidence_methodology_required")
    if not reason:
        return blocked("administrative_reason_required")
    linkages = claim_linkages(claim_id)
    if not linkages:
        return blocked("claim_source_linkage_required")
    related_conflicts = [
        item
        for item in current_conflicts()
        if claim_id in {item.get("claim_a_id"), item.get("claim_b_id")}
    ]
    score, components = _score(linkages, related_conflicts, limitations)
    if score < 20:
        band = "insufficient"
    elif score < 40:
        band = "limited"
    elif score < 60:
        band = "moderate"
    else:
        band = "substantial"
    explanation = {
        "methodology": methodology,
        "components": components,
        "limitations": limitations,
        "unresolved_conflict_ids": [
            item.get("conflict_id")
            for item in related_conflicts
            if item.get("resolution") == "unresolved"
        ],
        "source_linkage_ids": [item.get("linkage_id") for item in linkages],
        "score_cap": 79,
        "score_cap_reason": "high confidence requires later human review",
    }
    binding = {
        "claim_id": claim_id,
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "linkage_sha256": [item.get("linkage_sha256") for item in linkages],
        "conflict_event_sha256": [
            item.get("conflict_event_sha256") for item in related_conflicts
        ],
        "explanation_sha256": _sha(explanation),
    }
    content = {
        "event_type": ACTION,
        "claim_id": claim_id,
        "case_id": claim.get("case_id"),
        "entity_id": claim.get("entity_id"),
        "confidence_score": score,
        "confidence_band": band,
        "explanation": explanation,
        "confidence_binding": binding,
        "confidence_binding_sha256": _sha(binding),
        "reason": reason,
        "truth_assigned": False,
        "high_confidence_assigned": False,
        "human_review_complete": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "confidence_assessment_id": f"analytic-confidence-{digest[:24]}",
        "confidence_assessment_sha256": digest,
    }
    result = _record(actor, claim_id, event, ip_address)
    return {
        **result,
        "status": "analytic_confidence_assessed",
        "next_action": "human_analytic_review",
    }
