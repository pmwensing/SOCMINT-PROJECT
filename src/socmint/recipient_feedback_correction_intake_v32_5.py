from __future__ import annotations

from typing import Any

from . import database
from .delivery_attempt_receipt_ledger_v32_4 import find_delivery_receipt
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.recipient_feedback_correction_intake.v32_5"
VERSION = "v32.5.0"
FEEDBACK_ACTION = "dissemination_recipient_feedback_recorded"
CORRECTION_ACTION = "dissemination_correction_intake_recorded"
ALLOWED_FEEDBACK_TYPES = {
    "acknowledgement",
    "question",
    "clarification",
    "dispute",
    "error_report",
    "supplemental_information",
}
ALLOWED_SEVERITIES = {"informational", "low", "medium", "high", "critical"}
ALLOWED_CORRECTION_ACTIONS = {
    "no_change",
    "editorial_review",
    "new_revision_review",
    "recall_review",
}


def blocked(key: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key, **details}],
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "prior_feedback_mutated": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }


def _history(action: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=action)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "intake_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def recipient_feedback_history() -> list[dict[str, Any]]:
    return _history(FEEDBACK_ACTION)


def correction_intake_history() -> list[dict[str, Any]]:
    return _history(CORRECTION_ACTION)


def feedback_for_receipt(delivery_receipt_id: str | None = None) -> list[dict[str, Any]]:
    rows = recipient_feedback_history()
    if not delivery_receipt_id:
        return rows
    return [
        row
        for row in rows
        if row.get("delivery_receipt_id") == delivery_receipt_id
    ]


def corrections_for_feedback(recipient_feedback_id: str | None = None) -> list[dict[str, Any]]:
    rows = correction_intake_history()
    if not recipient_feedback_id:
        return rows
    return [
        row
        for row in rows
        if row.get("recipient_feedback_id") == recipient_feedback_id
    ]


def find_recipient_feedback(recipient_feedback_id: str) -> dict[str, Any] | None:
    for item in recipient_feedback_history():
        if item.get("recipient_feedback_id") == recipient_feedback_id:
            return item
    return None


def find_correction_intake(correction_intake_id: str) -> dict[str, Any] | None:
    for item in correction_intake_history():
        if item.get("correction_intake_id") == correction_intake_id:
            return item
    return None


def _record(
    *,
    actor: str,
    action: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target_value,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "intake_record_id": row.id,
            "recorded_by": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_recipient_feedback(
    *,
    recorder: str,
    delivery_receipt_id: str,
    feedback_type: str,
    severity: str,
    recipient_reference: str,
    summary: str,
    detail: str,
    confirmed: bool,
    source_reference: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    delivery_receipt_id = str(delivery_receipt_id or "").strip()
    feedback_type = str(feedback_type or "").strip().lower()
    severity = str(severity or "").strip().lower()
    recipient_reference = str(recipient_reference or "").strip()
    summary = str(summary or "").strip()
    detail = str(detail or "").strip()
    source_reference = str(source_reference or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_feedback_confirmation_required")
    if feedback_type not in ALLOWED_FEEDBACK_TYPES:
        return blocked("invalid_feedback_type")
    if severity not in ALLOWED_SEVERITIES:
        return blocked("invalid_feedback_severity")
    if not recipient_reference:
        return blocked("recipient_reference_required")
    if not summary:
        return blocked("feedback_summary_required")
    if not detail:
        return blocked("feedback_detail_required")

    receipt = find_delivery_receipt(delivery_receipt_id)
    if receipt is None:
        return blocked("delivered_receipt_required")
    if receipt.get("delivery_result") != "delivered":
        return blocked("delivered_receipt_required")
    if receipt.get("recipient_id") != recipient_reference:
        return blocked("feedback_recipient_receipt_mismatch")

    binding = {
        "delivery_receipt_id": delivery_receipt_id,
        "delivery_receipt_sha256": receipt.get("delivery_receipt_sha256"),
        "delivery_attempt_id": receipt.get("delivery_attempt_id"),
        "dissemination_package_id": receipt.get("dissemination_package_id"),
        "authorization_decision_id": receipt.get("authorization_decision_id"),
        "recipient_id": receipt.get("recipient_id"),
        "delivery_channel": receipt.get("delivery_channel"),
    }
    feedback_payload = {
        "feedback_type": feedback_type,
        "severity": severity,
        "summary": summary,
        "detail": detail,
        "source_reference": source_reference,
        "note": note,
    }
    content = {
        "event_type": FEEDBACK_ACTION,
        "case_id": receipt.get("case_id"),
        "delivery_receipt_id": delivery_receipt_id,
        "delivery_receipt_sha256": receipt.get("delivery_receipt_sha256"),
        "delivery_attempt_id": receipt.get("delivery_attempt_id"),
        "dissemination_package_id": receipt.get("dissemination_package_id"),
        "authorization_decision_id": receipt.get("authorization_decision_id"),
        "recipient_id": receipt.get("recipient_id"),
        "receipt_binding": binding,
        "receipt_binding_sha256": _sha(binding),
        "feedback_payload": feedback_payload,
        "feedback_payload_sha256": _sha(feedback_payload),
        "feedback_state": "recorded_pending_review",
        "correction_review_required": feedback_type in {"dispute", "error_report"}
        or severity in {"high", "critical"},
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "prior_feedback_mutated": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "recipient_feedback_id": f"recipient-feedback-{digest[:24]}",
        "recipient_feedback_sha256": digest,
    }
    if any(
        item.get("recipient_feedback_sha256") == digest
        for item in recipient_feedback_history()
    ):
        return blocked("recipient_feedback_already_exists")

    result = _record(
        actor=recorder,
        action=FEEDBACK_ACTION,
        target_value=event["recipient_feedback_id"],
        event=event,
        ip_address=ip_address,
    )
    return {
        **result,
        "status": "recipient_feedback_recorded",
        "next_action": (
            "record_correction_intake"
            if event["correction_review_required"]
            else "review_recipient_feedback"
        ),
    }


def record_correction_intake(
    *,
    reviewer: str,
    recipient_feedback_id: str,
    correction_action: str,
    reason: str,
    confirmed: bool,
    affected_section_ids: list[str] | None = None,
    proposed_resolution: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    recipient_feedback_id = str(recipient_feedback_id or "").strip()
    correction_action = str(correction_action or "").strip().lower()
    reason = str(reason or "").strip()
    proposed_resolution = str(proposed_resolution or "").strip()
    note = str(note or "").strip()
    sections = sorted(
        {
            str(value).strip()
            for value in (affected_section_ids or [])
            if str(value).strip()
        }
    )

    if confirmed is not True:
        return blocked("explicit_correction_intake_confirmation_required")
    if correction_action not in ALLOWED_CORRECTION_ACTIONS:
        return blocked("invalid_correction_action")
    if not reason:
        return blocked("correction_reason_required")
    if correction_action != "no_change" and not proposed_resolution:
        return blocked("proposed_resolution_required")

    feedback = find_recipient_feedback(recipient_feedback_id)
    if feedback is None:
        return blocked("recipient_feedback_required")

    binding = {
        "recipient_feedback_id": recipient_feedback_id,
        "recipient_feedback_sha256": feedback.get("recipient_feedback_sha256"),
        "delivery_receipt_id": feedback.get("delivery_receipt_id"),
        "delivery_attempt_id": feedback.get("delivery_attempt_id"),
        "dissemination_package_id": feedback.get("dissemination_package_id"),
        "authorization_decision_id": feedback.get("authorization_decision_id"),
        "case_id": feedback.get("case_id"),
    }
    review_payload = {
        "correction_action": correction_action,
        "affected_section_ids": sections,
        "reason": reason,
        "proposed_resolution": proposed_resolution,
        "note": note,
    }
    content = {
        "event_type": CORRECTION_ACTION,
        "case_id": feedback.get("case_id"),
        "recipient_feedback_id": recipient_feedback_id,
        "recipient_feedback_sha256": feedback.get("recipient_feedback_sha256"),
        "feedback_binding": binding,
        "feedback_binding_sha256": _sha(binding),
        "correction_review": review_payload,
        "correction_review_sha256": _sha(review_payload),
        "correction_state": "intake_recorded_pending_action",
        "new_revision_required": correction_action == "new_revision_review",
        "recall_review_required": correction_action == "recall_review",
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "prior_feedback_mutated": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "correction_intake_id": f"correction-intake-{digest[:24]}",
        "correction_intake_sha256": digest,
    }
    if any(
        item.get("correction_intake_sha256") == digest
        for item in correction_intake_history()
    ):
        return blocked("correction_intake_already_exists")

    result = _record(
        actor=reviewer,
        action=CORRECTION_ACTION,
        target_value=event["correction_intake_id"],
        event=event,
        ip_address=ip_address,
    )
    next_action = {
        "no_change": "close_feedback_review",
        "editorial_review": "perform_editorial_review",
        "new_revision_review": "assemble_new_draft_revision",
        "recall_review": "review_recall_and_lifecycle_history",
    }[correction_action]
    return {
        **result,
        "status": "correction_intake_recorded",
        "next_action": next_action,
    }
