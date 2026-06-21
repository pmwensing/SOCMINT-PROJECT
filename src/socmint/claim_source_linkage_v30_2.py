from __future__ import annotations

from typing import Any

from . import database
from .corroboration_claim_v30_1 import find_claim
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import current_artifacts, observations

SCHEMA = "socmint.claim_source_linkage.v30_2"
VERSION = "v30.2.0"
ACTION = "corroboration_claim_sources_linked"


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "evidence_mutated": False,
        "observation_mutated": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }


def linkage_history() -> list[dict[str, Any]]:
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


def claim_linkages(claim_id: str | None = None) -> list[dict[str, Any]]:
    rows = linkage_history()
    return (
        [row for row in rows if row.get("claim_id") == claim_id] if claim_id else rows
    )


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


def link_claim_sources(
    *,
    actor: str,
    claim_id: str,
    artifact_ids: list[str] | None,
    observation_ids: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    claim = find_claim(claim_id)
    reason = str(reason or "").strip()
    artifact_ids = sorted(
        {str(value).strip() for value in (artifact_ids or []) if str(value).strip()}
    )
    observation_ids = sorted(
        {str(value).strip() for value in (observation_ids or []) if str(value).strip()}
    )

    if claim is None:
        return blocked("corroboration_claim_required")
    if claim.get("claim_state") != "proposed":
        return blocked("proposed_claim_required")
    if confirmed is not True:
        return blocked("explicit_source_linkage_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")
    if not artifact_ids and not observation_ids:
        return blocked("evidence_or_observation_link_required")

    artifacts = {str(item.get("artifact_id")): item for item in current_artifacts()}
    observation_index = {
        str(item.get("observation_id")): item for item in observations()
    }
    missing_artifacts = [value for value in artifact_ids if value not in artifacts]
    missing_observations = [
        value for value in observation_ids if value not in observation_index
    ]
    if missing_artifacts:
        return blocked("evidence_artifact_not_found")
    if missing_observations:
        return blocked("observation_not_found")
    if any(
        artifacts[value].get("artifact_state") != "accepted" for value in artifact_ids
    ):
        return blocked("accepted_evidence_artifact_required")

    observation_artifact_ids = {
        str(observation_index[value].get("artifact_id")) for value in observation_ids
    }
    if artifact_ids and not observation_artifact_ids.issubset(set(artifact_ids)):
        return blocked("observation_artifact_binding_mismatch")

    artifact_bindings = [
        {
            "artifact_id": value,
            "content_sha256": artifacts[value].get("content_sha256"),
            "artifact_event_sha256": (
                artifacts[value].get("state_history") or [artifacts[value]]
            )[-1].get("artifact_event_sha256"),
        }
        for value in artifact_ids
    ]
    observation_bindings = [
        {
            "observation_id": value,
            "observation_sha256": observation_index[value].get("observation_sha256"),
            "artifact_id": observation_index[value].get("artifact_id"),
            "artifact_binding_sha256": observation_index[value].get(
                "artifact_binding_sha256"
            ),
        }
        for value in observation_ids
    ]
    source_manifest = {
        "claim_id": claim_id,
        "claim_event_sha256": claim.get("claim_event_sha256"),
        "artifact_bindings": artifact_bindings,
        "observation_bindings": observation_bindings,
    }
    linkage_sha256 = _sha(source_manifest)
    if any(
        row.get("linkage_sha256") == linkage_sha256 for row in claim_linkages(claim_id)
    ):
        return blocked("claim_source_linkage_already_exists")

    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": ACTION,
        "claim_id": claim_id,
        "case_id": claim.get("case_id"),
        "entity_id": claim.get("entity_id"),
        "source_manifest": source_manifest,
        "source_manifest_sha256": _sha(source_manifest),
        "linkage_id": f"claim-source-linkage-{linkage_sha256[:24]}",
        "linkage_sha256": linkage_sha256,
        "artifact_count": len(artifact_bindings),
        "observation_count": len(observation_bindings),
        "reason": reason,
        "evidence_mutated": False,
        "observation_mutated": False,
        "claim_mutated": False,
        "dossier_mutated": False,
    }
    result = _record(actor, claim_id, event, ip_address)
    return {
        **result,
        "status": "corroboration_claim_sources_linked",
        "next_action": "review_contradictions_and_disagreement",
    }
