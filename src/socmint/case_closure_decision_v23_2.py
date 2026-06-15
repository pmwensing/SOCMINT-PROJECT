from __future__ import annotations

from typing import Any

from . import database
from .case_closure_readiness_review_v23_1 import latest_closure_readiness_review
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.case_closure_decision.v23_2"
VERSION = "v23.2.0"
ACTION = "case_supervisor_closure_decision"
ALLOWED_DECISIONS = {"close", "hold", "return"}


def latest_supervisor_closure_decision(case_id: str) -> dict[str, Any] | None:
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
            "decision_record_id": row.id,
            "decided_by": row.actor,
            "decided_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_supervisor_closure_decision(
    case_id: str,
    *,
    decision: str,
    confirmed: bool,
    supervisor: str,
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
            "blockers": [{"key": "explicit_supervisor_closure_confirmation_required"}],
            "source_records_mutated": False,
        }
    if normalized not in ALLOWED_DECISIONS:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "invalid_supervisor_closure_decision"}],
            "source_records_mutated": False,
        }

    review = latest_closure_readiness_review(case_id)
    if review is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "closure_readiness_review_required"}],
            "source_records_mutated": False,
        }
    if review.get("decision") != "ready" or review.get(
        "ready_for_supervisor_closure_decision"
    ) is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "ready_closure_readiness_review_required"}],
            "source_records_mutated": False,
        }

    source = {
        "readiness_review_id": review.get("review_id"),
        "readiness_review_sha256": review.get("review_sha256"),
        "readiness_review_record_id": review.get("review_record_id"),
        "readiness_review_decision": review.get("decision"),
        "readiness_reviewed_by": review.get("reviewed_by"),
        "readiness_reviewed_at": review.get("reviewed_at"),
        "closure_summary": (review.get("source") or {}).get("closure_summary") or {},
    }
    source_sha256 = _sha(source)
    content = {
        "case_id": case_id,
        "decision": normalized,
        "note": str(note or "").strip(),
        "source": source,
        "source_sha256": source_sha256,
    }
    decision_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "closure_decision_id": f"closure-decision-{decision_sha256[:24]}",
        "closure_decision_sha256": decision_sha256,
        "case_closed": normalized == "close",
        "ready_for_retention_assignment": normalized == "close",
        "source_records_mutated": False,
        "retention_assignment_created": False,
        "archive_package_created": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=supervisor,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        decided_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    next_action = {
        "close": "assign_retention_policy",
        "hold": "review_closure_hold",
        "return": "return_case_to_closure_review",
    }[normalized]
    return {
        **event,
        "status": "closure_decision_recorded",
        "decision_record_id": record_id,
        "decided_by": supervisor,
        "decided_at": decided_at,
        "next_action": next_action,
    }
