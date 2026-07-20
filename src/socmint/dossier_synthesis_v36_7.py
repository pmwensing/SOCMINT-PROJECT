from __future__ import annotations

from typing import Any

from . import analytic_dossier_contribution_v30_6 as contribution_v30_6
from . import database
from .analytic_conflict_v30_3 import current_conflicts
from .claim_verification_v36_5 import find_verification
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .relationship_timeline_v36_6 import current_relationship_assessments

SCHEMA = "socmint.dossier_synthesis.v36_7"
VERSION = "v36.7.0"
ACTION = "dossier_synthesis_snapshot_created"
CATEGORIES = (
    "substantially_supported",
    "moderately_supported",
    "limited_support",
    "disputed",
    "insufficient",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "export_created": False,
        "published": False,
        "claim_mutated": False,
        "dossier_backend_mutated": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _audit_events(action: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=action)
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
    snapshot_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=snapshot_id,
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


def snapshot_history() -> list[dict[str, Any]]:
    return _audit_events(ACTION)


def current_snapshots() -> list[dict[str, Any]]:
    return sorted(
        snapshot_history(),
        key=lambda item: (
            str(item.get("case_id") or ""),
            str(item.get("entity_id") or ""),
            int(item.get("snapshot_version") or 0),
        ),
    )


def find_snapshot(snapshot_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in snapshot_history()
            if item.get("dossier_synthesis_snapshot_id") == snapshot_id
        ),
        None,
    )


def latest_snapshot(case_id: str, entity_id: str) -> dict[str, Any] | None:
    rows = [
        item
        for item in current_snapshots()
        if item.get("case_id") == case_id and item.get("entity_id") == entity_id
    ]
    return rows[-1] if rows else None


def _contribution_events() -> list[dict[str, Any]]:
    action = getattr(
        contribution_v30_6,
        "ACTION",
        "analytic_dossier_contribution_recorded",
    )
    return _audit_events(str(action))


def _current_contributions() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _contribution_events():
        claim_id = str(event.get("claim_id") or "")
        if claim_id:
            current[claim_id] = event
    return list(current.values())


def _decision(event: dict[str, Any]) -> str:
    return str(
        event.get("decision")
        or event.get("contribution_decision")
        or event.get("dossier_contribution_decision")
        or ""
    )


def _target_section(event: dict[str, Any]) -> str:
    return str(
        event.get("target_dossier_section")
        or event.get("dossier_section")
        or event.get("target_section")
        or "verified_claims"
    )


def _category(verification: dict[str, Any]) -> str:
    if verification.get("unresolved_conflict_ids"):
        return "disputed"
    band = str(verification.get("confidence_band") or "insufficient")
    if band == "substantial":
        return "substantially_supported"
    if band == "moderate":
        return "moderately_supported"
    if band == "limited":
        return "limited_support"
    return "insufficient"


def create_dossier_synthesis_snapshot(
    *,
    actor: str,
    case_id: str,
    entity_id: str,
    display_label: str,
    purpose: str,
    limitations: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    entity_id = _required(entity_id)
    display_label = _required(display_label)
    purpose = _required(purpose)
    reason = _required(reason)
    normalized_limitations = sorted(
        {
            _required(item)
            for item in (limitations or [])
            if _required(item)
        }
    )
    if confirmed is not True:
        return blocked("explicit_dossier_synthesis_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id or not entity_id:
        return blocked("case_and_entity_required")
    if not display_label or not purpose or not reason:
        return blocked("label_purpose_and_reason_required")

    approved = []
    for event in _current_contributions():
        if _decision(event) != "approved":
            continue
        claim = find_claim(str(event.get("claim_id") or ""))
        if claim is None:
            continue
        if str(claim.get("case_id") or "") != case_id:
            continue
        if str(claim.get("entity_id") or "") != entity_id:
            continue
        verification = find_verification(str(claim.get("claim_id") or ""))
        if verification is None:
            continue
        approved.append((event, claim, verification))
    if not approved:
        return blocked("approved_verified_dossier_contribution_required")

    related_conflicts = current_conflicts()
    relationships = current_relationship_assessments()
    section_map: dict[str, list[dict[str, Any]]] = {}
    category_map: dict[str, list[str]] = {key: [] for key in CATEGORIES}
    manifest = []
    for contribution, claim, verification in approved:
        claim_id = str(claim.get("claim_id") or "")
        category = _category(verification)
        item_relationships = [
            item
            for item in relationships
            if item.get("claim_id") == claim_id
        ]
        claim_conflicts = [
            item
            for item in related_conflicts
            if claim_id in {item.get("claim_a_id"), item.get("claim_b_id")}
        ]
        section = _target_section(contribution)
        entry = {
            "claim_id": claim_id,
            "claim_type": claim.get("claim_type"),
            "normalized_value": claim.get("normalized_value"),
            "category": category,
            "support_score": verification.get("support_score"),
            "confidence_band": verification.get("confidence_band"),
            "ranking": verification.get("ranking"),
            "source_ids": verification.get("source_ids"),
            "limitations": verification.get("limitations"),
            "unresolved_conflict_ids": verification.get(
                "unresolved_conflict_ids"
            ),
            "relationship_assessment_ids": [
                item.get("relationship_timeline_assessment_id")
                for item in item_relationships
            ],
            "contribution_decision_id": contribution.get(
                "dossier_contribution_id"
            )
            or contribution.get("contribution_id"),
            "claim_event_sha256": claim.get("claim_event_sha256"),
            "verification_sha256": verification.get(
                "claim_verification_assessment_sha256"
            ),
        }
        section_map.setdefault(section, []).append(entry)
        category_map[category].append(claim_id)
        manifest.append(
            {
                "claim_id": claim_id,
                "claim_event_sha256": claim.get("claim_event_sha256"),
                "verification_sha256": verification.get(
                    "claim_verification_assessment_sha256"
                ),
                "contribution_event_sha256": contribution.get(
                    "dossier_contribution_sha256"
                )
                or contribution.get("contribution_event_sha256"),
                "conflict_event_sha256": [
                    item.get("conflict_event_sha256")
                    for item in claim_conflicts
                ],
                "relationship_assessment_sha256": [
                    item.get("relationship_timeline_assessment_sha256")
                    for item in item_relationships
                ],
            }
        )
    for entries in section_map.values():
        entries.sort(key=lambda item: str(item.get("claim_id") or ""))
    manifest.sort(key=lambda item: str(item.get("claim_id") or ""))
    previous = latest_snapshot(case_id, entity_id)
    snapshot_version = int(previous.get("snapshot_version") or 0) + 1 if previous else 1
    snapshot = {
        "case_id": case_id,
        "entity_id": entity_id,
        "display_label": display_label,
        "purpose": purpose,
        "snapshot_version": snapshot_version,
        "sections": section_map,
        "categories": category_map,
        "coverage": {
            "approved_contribution_count": len(approved),
            "section_count": len(section_map),
            "substantial_count": len(category_map["substantially_supported"]),
            "moderate_count": len(category_map["moderately_supported"]),
            "disputed_count": len(category_map["disputed"]),
        },
        "limitations": normalized_limitations,
        "integrity_manifest": manifest,
        "integrity_manifest_sha256": _sha(manifest),
        "previous_snapshot_id": (
            previous.get("dossier_synthesis_snapshot_id") if previous else None
        ),
        "previous_snapshot_sha256": (
            previous.get("dossier_synthesis_snapshot_sha256") if previous else None
        ),
    }
    content = {
        "event_type": ACTION,
        **snapshot,
        "snapshot_sha256": _sha(snapshot),
        "reason": reason,
        "export_created": False,
        "published": False,
        "claim_mutated": False,
        "dossier_backend_mutated": False,
    }
    digest = _sha(content)
    snapshot_id = f"dossier-synthesis-{digest[:24]}"
    if find_snapshot(snapshot_id) is not None:
        return blocked("dossier_synthesis_snapshot_already_exists")
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "dossier_synthesis_snapshot_id": snapshot_id,
        "dossier_synthesis_snapshot_sha256": digest,
    }
    result = _record(actor, snapshot_id, event, ip_address)
    return {
        **result,
        "status": "dossier_synthesis_snapshot_created",
        "next_action": "review_snapshot_before_existing_export_pipeline",
    }
