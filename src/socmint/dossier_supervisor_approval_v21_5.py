from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_quality_review_v21_4 import build_dossier_quality_review

APPROVAL_SCHEMA = "socmint.dossier_supervisor_approval.v21_5"
APPROVAL_ACTION = "case_dossier_supervisor_approval"
VERSION = "v21.5.0"
ALLOWED_DECISIONS = {"approve", "return", "hold"}


def _latest_decision(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=APPROVAL_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "approval_record_id": row.id,
            "reviewer": row.actor,
            "decided_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def build_supervisor_approval_workspace(
    case_id: str,
    *,
    subject_id: int | None,
    ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review = build_dossier_quality_review(
        case_id,
        subject_id=subject_id,
        ledger_payload=ledger_payload,
    )
    latest = _latest_decision(case_id)
    return {
        "schema": APPROVAL_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "blocked" if review.get("status") == "blocked" else "reviewable",
        "quality_review": review,
        "review_ready": bool(review.get("ready")),
        "allowed_decisions": sorted(ALLOWED_DECISIONS),
        "can_approve": bool(review.get("ready")),
        "can_return": review.get("status") != "blocked",
        "can_hold": review.get("status") != "blocked",
        "latest_decision": latest,
        "next_action": (
            "record_supervisor_decision"
            if review.get("status") != "blocked"
            else review.get("next_action")
        ),
    }


def record_supervisor_dossier_decision(
    case_id: str,
    decision: str,
    *,
    subject_id: int,
    reviewer: str,
    note: str = "",
    ledger_payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    decision = str(decision or "").strip().lower()
    if decision not in ALLOWED_DECISIONS:
        return {
            "status": "blocked",
            "blockers": [{"key": "invalid_supervisor_decision"}],
        }
    review = build_dossier_quality_review(
        case_id,
        subject_id=subject_id,
        ledger_payload=ledger_payload,
    )
    if review.get("status") == "blocked":
        return {
            "status": "blocked",
            "blockers": review.get("blockers") or [{"key": "quality_review_required"}],
            "next_action": review.get("next_action"),
        }
    if decision == "approve" and not review.get("ready"):
        return {
            "status": "blocked",
            "blockers": [{"key": "ready_quality_review_required"}],
            "quality_review": review,
            "next_action": "resolve_dossier_quality_blockers",
        }

    result_status = {
        "approve": "approved",
        "return": "returned",
        "hold": "held",
    }[decision]
    next_action = {
        "approve": "prepare_final_export_package",
        "return": "revise_dossier_assembly",
        "hold": "await_supervisor_release",
    }[decision]
    decision_content = {
        "case_id": case_id,
        "subject_id": subject_id,
        "decision": decision,
        "result_status": result_status,
        "note": str(note or "").strip(),
        "source_review_id": review.get("review_id"),
        "source_review_sha256": review.get("review_sha256"),
        "source_review_ready": bool(review.get("ready")),
        "source_draft_id": review.get("draft_id"),
        "source_draft_sha256": review.get("draft_sha256"),
        "source_mapping_id": review.get("mapping_id"),
        "source_mapping_sha256": review.get("mapping_sha256"),
    }
    decision_sha256 = _sha(decision_content)
    event = {
        "schema": APPROVAL_SCHEMA,
        "version": VERSION,
        **decision_content,
        "approval_id": f"dossier-approval-{decision_sha256[:24]}",
        "decision_sha256": decision_sha256,
        "export_preparation": {
            "eligible": decision == "approve",
            "status": "ready_for_export_package" if decision == "approve" else "not_ready",
            "next_action": next_action,
        },
        "draft_mutated": False,
        "quality_review_snapshot_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=reviewer,
            action=APPROVAL_ACTION,
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
    return {
        **event,
        "status": result_status,
        "approval_record_id": record_id,
        "reviewer": reviewer,
        "decided_at": decided_at,
        "next_action": next_action,
    }
