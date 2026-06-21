from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .draft_dossier_revision_v31_2 import current_draft_revisions
from .editorial_validation_v31_3 import current_editorial_validations

SCHEMA = "socmint.human_release_approval.v31_4"
VERSION = "v31.4.0"
ACTION = "draft_dossier_human_release_decision_recorded"
ALLOWED_DECISIONS = {"approve", "return", "hold"}


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "draft_revision_mutated": False,
        "editorial_validation_mutated": False,
        "publication_performed": False,
        "published_revision_created": False,
        "published_revision_mutated": False,
    }


def release_approval_history() -> list[dict[str, Any]]:
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
                "approval_record_id": row.id,
                "reviewer": row.actor,
                "decided_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def approvals_for_revision(draft_revision_id: str | None = None) -> list[dict[str, Any]]:
    rows = release_approval_history()
    if not draft_revision_id:
        return rows
    return [row for row in rows if row.get("draft_revision_id") == draft_revision_id]


def current_release_approvals() -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    histories: dict[str, list[dict[str, Any]]] = {}
    for item in release_approval_history():
        approval_id = str(item.get("release_approval_id") or "")
        if not approval_id:
            continue
        histories.setdefault(approval_id, []).append(item)
        latest[approval_id] = dict(item)
    for approval_id, item in latest.items():
        item["approval_history"] = histories.get(approval_id, [])
    return sorted(latest.values(), key=lambda item: str(item.get("release_approval_id")))


def find_draft_revision(draft_revision_id: str) -> dict[str, Any] | None:
    for item in current_draft_revisions():
        if item.get("draft_revision_id") == draft_revision_id:
            return item
    return None


def latest_editorial_validation(draft_revision_id: str) -> dict[str, Any] | None:
    rows = [
        item
        for item in current_editorial_validations()
        if item.get("draft_revision_id") == draft_revision_id
    ]
    return rows[-1] if rows else None


def _record(
    reviewer: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=reviewer,
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
            "approval_record_id": row.id,
            "reviewer": reviewer,
            "decided_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_human_release_decision(
    *,
    reviewer: str,
    draft_revision_id: str,
    decision: str,
    note: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    draft_revision_id = str(draft_revision_id or "").strip()
    decision = str(decision or "").strip().lower()
    note = str(note or "").strip()
    reason = str(reason or "").strip()

    if decision not in ALLOWED_DECISIONS:
        return blocked("invalid_human_release_decision")
    revision = find_draft_revision(draft_revision_id)
    if revision is None:
        return blocked("draft_dossier_revision_required")
    validation = latest_editorial_validation(draft_revision_id)
    if validation is None:
        return blocked("editorial_validation_required")
    if confirmed is not True:
        return blocked("explicit_human_release_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")
    if decision == "approve" and validation.get("gate_status") != "passed":
        return blocked("passing_editorial_validation_required")
    if validation.get("draft_revision_sha256") != revision.get("draft_revision_sha256"):
        return blocked("current_draft_revision_validation_required")

    result_status = {
        "approve": "approved",
        "return": "returned",
        "hold": "held",
    }[decision]
    next_action = {
        "approve": "create_immutable_published_revision",
        "return": "revise_draft_dossier_revision",
        "hold": "await_human_release_decision",
    }[decision]
    binding = {
        "draft_revision_id": draft_revision_id,
        "draft_revision_sha256": revision.get("draft_revision_sha256"),
        "editorial_validation_id": validation.get("editorial_validation_id"),
        "editorial_validation_sha256": validation.get("editorial_validation_sha256"),
        "publication_candidate_id": revision.get("publication_candidate_id"),
        "publication_candidate_sha256": revision.get("publication_candidate_sha256"),
        "source_manifest_sha256": revision.get("source_manifest_sha256"),
        "draft_sections_sha256": revision.get("draft_sections_sha256"),
    }
    content = {
        "event_type": ACTION,
        "decision": decision,
        "result_status": result_status,
        "draft_revision_id": draft_revision_id,
        "draft_revision_sha256": revision.get("draft_revision_sha256"),
        "editorial_validation_id": validation.get("editorial_validation_id"),
        "editorial_validation_sha256": validation.get("editorial_validation_sha256"),
        "editorial_gate_status": validation.get("gate_status"),
        "publication_candidate_id": revision.get("publication_candidate_id"),
        "case_id": revision.get("case_id"),
        "subject_id": revision.get("subject_id"),
        "release_scope": validation.get("release_scope"),
        "note": note,
        "reason": reason,
        "human_confirmed": True,
        "approval_binding": binding,
        "approval_binding_sha256": _sha(binding),
        "publication_eligibility": {
            "eligible": decision == "approve",
            "status": "ready_for_immutable_publication" if decision == "approve" else "not_ready",
            "next_action": next_action,
        },
        "draft_revision_mutated": False,
        "editorial_validation_mutated": False,
        "publication_performed": False,
        "published_revision_created": False,
        "published_revision_mutated": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "release_approval_id": f"human-release-approval-{digest[:24]}",
        "release_approval_sha256": digest,
    }
    if any(
        item.get("release_approval_sha256") == digest
        for item in release_approval_history()
    ):
        return blocked("human_release_decision_already_exists")

    result = _record(reviewer, event["release_approval_id"], event, ip_address)
    return {
        **result,
        "status": result_status,
        "next_action": next_action,
    }
