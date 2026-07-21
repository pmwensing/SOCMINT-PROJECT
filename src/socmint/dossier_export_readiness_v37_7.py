from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_synthesis_v36_7 import find_snapshot
from .guided_analyst_workflow_v37_5 import build_guided_analyst_workflow
from .relationship_chronology_workflow_v37_6 import build_relationship_chronology

SCHEMA = "socmint.dossier_export_readiness.v37_7"
VERSION = "v37.7.0"
ACTION = "dossier_export_readiness_recorded"


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "export_created": False,
        "published": False,
        "dossier_mutated": False,
        "snapshot_mutated": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_required(item) for item in value if _required(item)})


def _history() -> list[dict[str, Any]]:
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


def _record(
    actor: str,
    readiness_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=readiness_id,
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


def current_export_readiness_records() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        snapshot_id = str(event.get("dossier_synthesis_snapshot_id") or "")
        if snapshot_id:
            current[snapshot_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_export_readiness(readiness_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in _history()
            if item.get("dossier_export_readiness_id") == readiness_id
        ),
        None,
    )


def assess_dossier_export_readiness(
    *,
    actor: str,
    snapshot_id: str,
    redaction_review_id: str,
    scope_review_id: str,
    quality_gate_reference: str,
    approval_reference: str,
    manifest_reference: str,
    chronology_reviewed: bool,
    unresolved_exceptions: list[str] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    snapshot_id = _required(snapshot_id)
    redaction_review_id = _required(redaction_review_id)
    scope_review_id = _required(scope_review_id)
    quality_gate_reference = _required(quality_gate_reference)
    approval_reference = _required(approval_reference)
    manifest_reference = _required(manifest_reference)
    exceptions = _string_list(unresolved_exceptions)
    reason = _required(reason)
    if confirmed is not True:
        return blocked("explicit_export_readiness_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not snapshot_id:
        return blocked("dossier_snapshot_id_required")
    if not all(
        (
            redaction_review_id,
            scope_review_id,
            quality_gate_reference,
            approval_reference,
            manifest_reference,
        )
    ):
        return blocked("redaction_scope_quality_approval_and_manifest_references_required")
    if chronology_reviewed is not True:
        return blocked("chronology_review_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")

    snapshot = find_snapshot(snapshot_id)
    if snapshot is None:
        return blocked("dossier_synthesis_snapshot_required")
    case_id = _required(snapshot.get("case_id"))
    entity_id = _required(snapshot.get("entity_id"))
    if not case_id or not entity_id:
        return blocked("snapshot_case_and_entity_binding_required")

    workflow = build_guided_analyst_workflow()
    chronology = build_relationship_chronology(case_id=case_id, entity_id=entity_id)
    integrity_findings = [
        item
        for item in (workflow.get("findings") or [])
        if isinstance(item, dict) and item.get("severity") == "integrity_alert"
    ]
    unresolved_conflict_count = sum(
        int(item.get("count") or 0)
        for item in (workflow.get("findings") or [])
        if isinstance(item, dict)
        and item.get("key") in {"verified_claims_disputed", "alternative_ranking_tied"}
    )
    readiness_blockers = []
    if integrity_findings:
        readiness_blockers.append("workflow_integrity_findings_unresolved")
    if unresolved_conflict_count:
        readiness_blockers.append("claim_conflicts_or_ranking_ties_unresolved")
    if exceptions:
        readiness_blockers.append("declared_unresolved_exceptions")
    if not chronology.get("entries"):
        readiness_blockers.append("reviewed_chronology_empty")

    bindings = {
        "snapshot_id": snapshot_id,
        "snapshot_sha256": snapshot.get("dossier_synthesis_snapshot_sha256"),
        "integrity_manifest_sha256": snapshot.get("integrity_manifest_sha256"),
        "case_id": case_id,
        "entity_id": entity_id,
        "redaction_review_id": redaction_review_id,
        "scope_review_id": scope_review_id,
        "quality_gate_reference": quality_gate_reference,
        "approval_reference": approval_reference,
        "manifest_reference": manifest_reference,
        "workflow_summary": workflow.get("summary") or {},
        "chronology_summary": chronology.get("summary") or {},
        "workflow_findings_sha256": _sha(workflow.get("findings") or []),
        "chronology_entries_sha256": _sha(chronology.get("entries") or []),
    }
    ready = not readiness_blockers
    content = {
        "event_type": ACTION,
        "dossier_synthesis_snapshot_id": snapshot_id,
        "case_id": case_id,
        "entity_id": entity_id,
        "bindings": bindings,
        "bindings_sha256": _sha(bindings),
        "readiness_status": "ready" if ready else "not_ready",
        "readiness_blockers": readiness_blockers,
        "integrity_findings": integrity_findings,
        "unresolved_conflict_count": unresolved_conflict_count,
        "unresolved_exceptions": exceptions,
        "reason": reason,
        "export_created": False,
        "published": False,
        "dossier_mutated": False,
        "snapshot_mutated": False,
        "existing_export_services_remain_authoritative": True,
    }
    digest = _sha(content)
    readiness_id = f"dossier-export-readiness-{digest[:24]}"
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "dossier_export_readiness_id": readiness_id,
        "dossier_export_readiness_sha256": digest,
    }
    result = _record(actor, readiness_id, event, ip_address)
    return {
        **result,
        "status": "dossier_export_readiness_recorded",
        "next_action": (
            "submit_to_existing_export_approval_gate"
            if ready
            else "resolve_readiness_blockers"
        ),
    }
