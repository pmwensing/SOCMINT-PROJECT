from __future__ import annotations

from typing import Any

from . import database
from .case_closure_workspace_v23_0 import build_case_closure_workspace
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.case_closure_readiness_review.v23_1"
VERSION = "v23.1.0"
ACTION = "case_closure_readiness_review"
ALLOWED_DECISIONS = {"ready", "not_ready"}


def latest_closure_readiness_review(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "review_record_id": row.id,
            "reviewed_by": row.actor,
            "reviewed_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def review_case_closure_readiness(
    case_id: str,
    *,
    decision: str,
    confirmed: bool,
    reviewer: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    normalized = str(decision or "").strip().lower()
    if confirmed is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "explicit_closure_readiness_confirmation_required"}],
            "source_records_mutated": False,
        }
    if normalized not in ALLOWED_DECISIONS:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "invalid_closure_readiness_decision"}],
            "source_records_mutated": False,
        }

    workspace = build_case_closure_workspace(case_id)
    if normalized == "ready" and workspace.get("closure_eligible") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": workspace.get("blockers") or [
                {"key": "closure_eligibility_required"}
            ],
            "source_records_mutated": False,
        }

    source_summary = workspace.get("release_history", {}).get("closure_summary") or {}
    source = {
        "closure_workspace_version": workspace.get("version"),
        "closure_workspace_status": workspace.get("status"),
        "closure_eligible": workspace.get("closure_eligible") is True,
        "archive_ready": workspace.get("archive_ready") is True,
        "current_release_outcome": workspace.get("current_release_outcome"),
        "closure_summary": source_summary,
        "closure_blockers": workspace.get("blockers") or [],
        "proposed_retention_policy_id": (
            workspace.get("proposed_retention_policy") or {}
        ).get("policy_id"),
    }
    source_sha256 = _sha(source)
    content = {
        "case_id": case_id,
        "decision": normalized,
        "note": str(note or "").strip(),
        "source": source,
        "source_sha256": source_sha256,
    }
    review_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "review_id": f"closure-readiness-{review_sha256[:24]}",
        "review_sha256": review_sha256,
        "ready_for_supervisor_closure_decision": normalized == "ready",
        "source_records_mutated": False,
        "closure_record_created": False,
        "retention_assignment_created": False,
        "archive_package_created": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=reviewer,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        reviewed_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "review_recorded",
        "review_record_id": record_id,
        "reviewed_by": reviewer,
        "reviewed_at": reviewed_at,
        "next_action": (
            "record_supervisor_closure_decision"
            if normalized == "ready"
            else "resolve_closure_readiness_blockers"
        ),
    }
