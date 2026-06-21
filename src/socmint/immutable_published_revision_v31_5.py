from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .draft_dossier_revision_v31_2 import current_draft_revisions
from .human_release_approval_v31_4 import approvals_for_revision

SCHEMA = "socmint.immutable_published_revision.v31_5"
VERSION = "v31.5.0"
ACTION = "immutable_published_revision_created"


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "draft_revision_mutated": False,
        "release_approval_mutated": False,
        "prior_published_revision_mutated": False,
        "external_transmission_performed": False,
    }


def published_revision_history() -> list[dict[str, Any]]:
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
                "publication_record_id": row.id,
                "publisher": row.actor,
                "published_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def current_published_revisions() -> list[dict[str, Any]]:
    return sorted(
        published_revision_history(),
        key=lambda item: str(item.get("published_revision_id") or ""),
    )


def published_revisions_for_case(case_id: str | None = None) -> list[dict[str, Any]]:
    rows = published_revision_history()
    if not case_id:
        return rows
    return [row for row in rows if row.get("case_id") == case_id]


def find_draft_revision(draft_revision_id: str) -> dict[str, Any] | None:
    for item in current_draft_revisions():
        if item.get("draft_revision_id") == draft_revision_id:
            return item
    return None


def latest_release_decision(draft_revision_id: str) -> dict[str, Any] | None:
    rows = approvals_for_revision(draft_revision_id)
    return rows[-1] if rows else None


def _record(
    publisher: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=publisher,
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
            "publication_record_id": row.id,
            "publisher": publisher,
            "published_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def create_immutable_published_revision(
    *,
    publisher: str,
    draft_revision_id: str,
    publication_label: str,
    publication_note: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    draft_revision_id = str(draft_revision_id or "").strip()
    publication_label = str(publication_label or "").strip()
    publication_note = str(publication_note or "").strip()
    reason = str(reason or "").strip()

    revision = find_draft_revision(draft_revision_id)
    if revision is None:
        return blocked("draft_dossier_revision_required")
    approval = latest_release_decision(draft_revision_id)
    if approval is None or approval.get("result_status") != "approved":
        return blocked("approved_human_release_decision_required")
    if confirmed is not True:
        return blocked("explicit_publication_confirmation_required")
    if not publication_label:
        return blocked("publication_label_required")
    if not reason:
        return blocked("administrative_reason_required")
    if approval.get("draft_revision_sha256") != revision.get("draft_revision_sha256"):
        return blocked("current_draft_revision_approval_required")
    if approval.get("publication_eligibility", {}).get("eligible") is not True:
        return blocked("publication_eligibility_required")
    if any(
        item.get("release_approval_sha256") == approval.get("release_approval_sha256")
        for item in published_revision_history()
    ):
        return blocked("release_approval_already_published")

    published_content = {
        "sections": revision.get("draft_sections") or [],
        "candidate_contribution_entry": revision.get("candidate_contribution_entry") or {},
        "section_count": len(revision.get("draft_sections") or []),
    }
    provenance = {
        "draft_revision_id": draft_revision_id,
        "draft_revision_sha256": revision.get("draft_revision_sha256"),
        "publication_candidate_id": revision.get("publication_candidate_id"),
        "publication_candidate_sha256": revision.get("publication_candidate_sha256"),
        "dossier_contribution_id": revision.get("dossier_contribution_id"),
        "source_manifest_sha256": revision.get("source_manifest_sha256"),
        "draft_sections_sha256": revision.get("draft_sections_sha256"),
        "release_approval_id": approval.get("release_approval_id"),
        "release_approval_sha256": approval.get("release_approval_sha256"),
        "editorial_validation_id": approval.get("editorial_validation_id"),
        "editorial_validation_sha256": approval.get("editorial_validation_sha256"),
    }
    metadata = {
        "publication_label": publication_label,
        "publication_note": publication_note,
        "reason": reason,
        "case_id": revision.get("case_id"),
        "subject_id": revision.get("subject_id"),
        "release_scope": approval.get("release_scope"),
        "format": "socmint-json",
        "media_type": "application/json",
        "revision_state": "published",
    }
    integrity = {
        "published_content_sha256": _sha(published_content),
        "provenance_sha256": _sha(provenance),
        "metadata_sha256": _sha(metadata),
    }
    content = {
        "event_type": ACTION,
        "case_id": revision.get("case_id"),
        "subject_id": revision.get("subject_id"),
        "revision_state": "published",
        "publication_label": publication_label,
        "publication_note": publication_note,
        "reason": reason,
        "published_content": published_content,
        "provenance": provenance,
        "metadata": metadata,
        "integrity": integrity,
        "release_approval_id": approval.get("release_approval_id"),
        "release_approval_sha256": approval.get("release_approval_sha256"),
        "supersedes_published_revision_id": None,
        "immutable": True,
        "draft_revision_mutated": False,
        "release_approval_mutated": False,
        "prior_published_revision_mutated": False,
        "external_transmission_performed": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "published_revision_id": f"published-dossier-revision-{digest[:24]}",
        "published_revision_sha256": digest,
    }
    if any(
        item.get("published_revision_sha256") == digest
        for item in published_revision_history()
    ):
        return blocked("published_revision_already_exists")

    result = _record(publisher, event["published_revision_id"], event, ip_address)
    return {
        **result,
        "status": "published_revision_created",
        "next_action": "manage_supersession_and_revision_history",
    }
