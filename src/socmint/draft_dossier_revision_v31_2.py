from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
    build_dossier_assembly_workspace,
)
from .publication_candidate_v31_1 import find_candidate

SCHEMA = "socmint.draft_dossier_revision.v31_2"
VERSION = "v31.2.0"
ACTION = "draft_dossier_revision_assembled"


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "candidate_mutated": False,
        "source_dossier_mutated": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "published_revision_mutated": False,
    }


def draft_revision_history() -> list[dict[str, Any]]:
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


def revisions_for_candidate(candidate_id: str | None = None) -> list[dict[str, Any]]:
    rows = draft_revision_history()
    if not candidate_id:
        return rows
    return [row for row in rows if row.get("publication_candidate_id") == candidate_id]


def current_draft_revisions() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in draft_revision_history():
        revision_id = str(item.get("draft_revision_id") or "")
        if not revision_id:
            continue
        histories.setdefault(revision_id, []).append(item)
        latest[revision_id] = dict(item)
    for revision_id, item in latest.items():
        item["revision_history"] = histories.get(revision_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("draft_revision_id")))


def _record(
    actor: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=target_value,
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


def assemble_draft_dossier_revision(
    *,
    actor: str,
    publication_candidate_id: str,
    revision_label: str,
    editorial_note: str,
    reason: str,
    confirmed: bool,
    subject_id: int | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    publication_candidate_id = str(publication_candidate_id or "").strip()
    revision_label = str(revision_label or "").strip()
    editorial_note = str(editorial_note or "").strip()
    reason = str(reason or "").strip()

    candidate = find_candidate(publication_candidate_id)
    if candidate is None:
        return blocked("proposed_publication_candidate_required")
    if candidate.get("candidate_state") != "proposed":
        return blocked("proposed_publication_candidate_required")
    if confirmed is not True:
        return blocked("explicit_draft_revision_confirmation_required")
    if not revision_label:
        return blocked("draft_revision_label_required")
    if not editorial_note:
        return blocked("editorial_note_required")
    if not reason:
        return blocked("administrative_reason_required")

    case_id = str(candidate.get("case_id") or "").strip()
    if not case_id:
        return blocked("candidate_case_binding_required")

    assembly = build_dossier_assembly_workspace(case_id, subject_id=subject_id)
    source_package = assembly.get("source_package") or {}
    source_manifest = {
        "case_id": case_id,
        "subject_id": subject_id,
        "assembly_schema": assembly.get("schema"),
        "assembly_version": assembly.get("version"),
        "source_package_id": source_package.get("package_id"),
        "source_package_manifest_sha256": source_package.get("manifest_sha256"),
        "section_manifest_sha256": _sha(assembly.get("sections") or []),
        "gap_manifest_sha256": _sha(assembly.get("gaps") or []),
        "publication_candidate_id": publication_candidate_id,
        "publication_candidate_sha256": candidate.get("publication_candidate_sha256"),
        "dossier_contribution_id": candidate.get("dossier_contribution_id"),
        "candidate_binding_sha256": candidate.get("candidate_binding_sha256"),
    }
    draft_sections = list(assembly.get("sections") or [])
    target_section = str(candidate.get("target_section") or "").strip()
    contribution_entry = {
        "entry_type": "approved_analytic_contribution",
        "dossier_contribution_id": candidate.get("dossier_contribution_id"),
        "claim_id": candidate.get("claim_id"),
        "entity_id": candidate.get("entity_id"),
        "target_section": target_section or None,
        "publication_candidate_id": publication_candidate_id,
        "publication_candidate_sha256": candidate.get("publication_candidate_sha256"),
    }
    content = {
        "event_type": ACTION,
        "revision_state": "draft",
        "revision_label": revision_label,
        "editorial_note": editorial_note,
        "reason": reason,
        "publication_candidate_id": publication_candidate_id,
        "publication_candidate_sha256": candidate.get("publication_candidate_sha256"),
        "dossier_contribution_id": candidate.get("dossier_contribution_id"),
        "case_id": case_id,
        "subject_id": subject_id,
        "target_section": target_section or None,
        "source_manifest": source_manifest,
        "source_manifest_sha256": _sha(source_manifest),
        "draft_sections": draft_sections,
        "draft_sections_sha256": _sha(draft_sections),
        "candidate_contribution_entry": contribution_entry,
        "candidate_contribution_entry_sha256": _sha(contribution_entry),
        "assembly_gap_count": assembly.get("gap_count", 0),
        "source_dossier_status": assembly.get("status"),
        "candidate_mutated": False,
        "source_dossier_mutated": False,
        "release_approval_performed": False,
        "publication_performed": False,
        "published_revision_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "draft_revision_id": f"draft-dossier-revision-{digest[:24]}",
        "draft_revision_sha256": digest,
    }
    if any(
        item.get("draft_revision_sha256") == digest
        for item in draft_revision_history()
    ):
        return blocked("draft_dossier_revision_already_exists")

    result = _record(actor, event["draft_revision_id"], event, ip_address)
    return {
        **result,
        "status": "draft_dossier_revision_assembled",
        "next_action": "run_editorial_validation_and_policy_gate",
    }
