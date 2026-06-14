from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .dossier_delivery_receipt_v22_4 import (
    latest_delivery_receipt,
    latest_recipient_acknowledgement,
)
from .dossier_secure_distribution_v22_3 import latest_secure_distribution

SCHEMA = "socmint.dossier_delivery_recovery_controls.v22_5"
VERSION = "v22.5.0"
FAILURE_REVIEW_ACTION = "case_dossier_failed_delivery_review"
RECALL_ACTION = "case_dossier_recall_request"
REISSUE_ACTION = "case_dossier_reissue_authorization"


def _latest(case_id: str, action: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=action, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "record_id": row.id,
            "recorded_by": row.actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def latest_failed_delivery_review(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, FAILURE_REVIEW_ACTION)


def latest_recall_request(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, RECALL_ACTION)


def latest_reissue_authorization(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, REISSUE_ACTION)


def build_delivery_recovery_state(case_id: str) -> dict[str, Any]:
    distribution = latest_secure_distribution(case_id)
    receipt = latest_delivery_receipt(case_id)
    acknowledgement = latest_recipient_acknowledgement(case_id)
    failed_review = latest_failed_delivery_review(case_id)
    recall = latest_recall_request(case_id)
    reissue = latest_reissue_authorization(case_id)
    delivery_failed = bool(receipt and receipt.get("delivery_result") == "failed")
    delivered = bool(receipt and receipt.get("delivery_result") == "delivered")
    ack_received = bool(acknowledgement)
    recall_available = bool(distribution and not ack_received)
    reissue_available = bool(distribution and (delivery_failed or recall))
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "tracking",
        "distribution": distribution,
        "delivery_receipt": receipt,
        "recipient_acknowledgement": acknowledgement,
        "latest_failed_delivery_review": failed_review,
        "latest_recall_request": recall,
        "latest_reissue_authorization": reissue,
        "delivery_failed": delivery_failed,
        "delivery_succeeded": delivered,
        "acknowledgement_received": ack_received,
        "failed_delivery_review_required": delivery_failed and failed_review is None,
        "recall_available": recall_available,
        "reissue_available": reissue_available,
        "dispatch_record_mutated": False,
        "delivery_receipt_mutated": False,
        "acknowledgement_record_mutated": False,
        "next_action": (
            "review_failed_delivery"
            if delivery_failed and failed_review is None
            else "request_recall"
            if recall_available and recall is None
            else "authorize_reissue"
            if reissue_available and reissue is None
            else "monitor_delivery_recovery"
        ),
    }


def _record(case_id: str, action: str, actor: str, event: dict[str, Any], ip_address: str | None) -> tuple[int, str | None]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id, row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()


def review_failed_delivery(
    case_id: str,
    *,
    confirmed: bool,
    reviewer: str,
    root_cause: str,
    resolution_plan: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "explicit_failed_delivery_review_confirmation_required"}]}
    receipt = latest_delivery_receipt(case_id)
    if receipt is None or receipt.get("delivery_result") != "failed":
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "failed_delivery_receipt_required"}]}
    content = {
        "case_id": case_id,
        "delivery_receipt_id": receipt.get("delivery_receipt_id"),
        "delivery_receipt_sha256": receipt.get("delivery_receipt_sha256"),
        "distribution_id": receipt.get("distribution_id"),
        "export_package_id": receipt.get("export_package_id"),
        "recipient_id": receipt.get("recipient_id"),
        "failure_code": receipt.get("failure_code"),
        "failure_detail": receipt.get("failure_detail"),
        "root_cause": str(root_cause or "").strip(),
        "resolution_plan": str(resolution_plan or "").strip(),
        "note": str(note or "").strip(),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "failed_delivery_review_id": f"failed-review-{digest[:24]}",
        "failed_delivery_review_sha256": digest,
        "dispatch_record_mutated": False,
        "delivery_receipt_mutated": False,
    }
    record_id, recorded_at = _record(case_id, FAILURE_REVIEW_ACTION, reviewer, event, ip_address)
    return {**event, "status": "failed_delivery_review_recorded", "record_id": record_id, "recorded_by": reviewer, "recorded_at": recorded_at, "next_action": "request_recall_or_authorize_reissue"}


def request_recall(
    case_id: str,
    *,
    confirmed: bool,
    requester: str,
    reason: str,
    scope: str = "recipient_access",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "explicit_recall_confirmation_required"}]}
    distribution = latest_secure_distribution(case_id)
    acknowledgement = latest_recipient_acknowledgement(case_id)
    if distribution is None:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "secure_distribution_required"}]}
    if acknowledgement is not None:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "recall_blocked_after_recipient_acknowledgement"}]}
    request = distribution.get("dispatch_request") or {}
    content = {
        "case_id": case_id,
        "distribution_id": distribution.get("distribution_id"),
        "dispatch_request_sha256": distribution.get("dispatch_request_sha256"),
        "export_package_id": request.get("export_package_id"),
        "recipient_id": request.get("recipient_id"),
        "delivery_channel": request.get("delivery_channel"),
        "reason": str(reason or "").strip(),
        "scope": str(scope or "recipient_access").strip(),
        "note": str(note or "").strip(),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "recall_request_id": f"recall-{digest[:24]}",
        "recall_request_sha256": digest,
        "dispatch_record_mutated": False,
        "delivery_receipt_mutated": False,
        "acknowledgement_record_mutated": False,
    }
    record_id, recorded_at = _record(case_id, RECALL_ACTION, requester, event, ip_address)
    return {**event, "status": "recall_requested", "record_id": record_id, "recorded_by": requester, "recorded_at": recorded_at, "next_action": "review_recall_outcome"}


def authorize_reissue(
    case_id: str,
    *,
    confirmed: bool,
    authorizer: str,
    target_recipient_id: str,
    target_delivery_channel: str,
    reason: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "explicit_reissue_confirmation_required"}]}
    distribution = latest_secure_distribution(case_id)
    receipt = latest_delivery_receipt(case_id)
    recall = latest_recall_request(case_id)
    if distribution is None:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "secure_distribution_required"}]}
    if not (receipt and receipt.get("delivery_result") == "failed") and recall is None:
        return {"schema": SCHEMA, "version": VERSION, "case_id": case_id, "status": "blocked", "blockers": [{"key": "failed_delivery_or_recall_required"}]}
    request = distribution.get("dispatch_request") or {}
    history = {
        "original_distribution_id": distribution.get("distribution_id"),
        "original_dispatch_request_sha256": distribution.get("dispatch_request_sha256"),
        "original_export_package_id": request.get("export_package_id"),
        "original_recipient_id": request.get("recipient_id"),
        "original_delivery_channel": request.get("delivery_channel"),
        "delivery_receipt_id": (receipt or {}).get("delivery_receipt_id"),
        "delivery_result": (receipt or {}).get("delivery_result"),
        "recall_request_id": (recall or {}).get("recall_request_id"),
    }
    content = {
        "case_id": case_id,
        "history": history,
        "target_recipient_id": str(target_recipient_id or "").strip(),
        "target_delivery_channel": str(target_delivery_channel or "").strip(),
        "reason": str(reason or "").strip(),
        "note": str(note or "").strip(),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "reissue_authorization_id": f"reissue-{digest[:24]}",
        "reissue_authorization_sha256": digest,
        "authorized": True,
        "dispatch_record_mutated": False,
        "delivery_receipt_mutated": False,
        "acknowledgement_record_mutated": False,
        "recall_record_mutated": False,
    }
    record_id, recorded_at = _record(case_id, REISSUE_ACTION, authorizer, event, ip_address)
    return {**event, "status": "reissue_authorized", "record_id": record_id, "recorded_by": authorizer, "recorded_at": recorded_at, "next_action": "return_to_dossier_release_workspace"}
