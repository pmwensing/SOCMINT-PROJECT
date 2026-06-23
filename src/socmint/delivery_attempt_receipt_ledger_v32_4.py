from __future__ import annotations

from typing import Any

from . import database
from .authorization_policy_release_gate_v32_3 import decisions_for_package
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dissemination_package_v32_2 import find_dissemination_package

SCHEMA = "socmint.delivery_attempt_receipt_ledger.v32_4"
VERSION = "v32.4.0"
ATTEMPT_ACTION = "dissemination_delivery_attempt_recorded"
RECEIPT_ACTION = "dissemination_delivery_receipt_recorded"
ALLOWED_ATTEMPT_RESULTS = {"accepted", "failed", "blocked"}
ALLOWED_RECEIPT_RESULTS = {"delivered", "failed", "pending"}


def blocked(key: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key, **details}],
        "transport_invoked_by_ledger": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "prior_attempt_mutated": False,
        "prior_receipt_mutated": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
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
                "ledger_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def delivery_attempt_history() -> list[dict[str, Any]]:
    return _history(ATTEMPT_ACTION)


def delivery_receipt_history() -> list[dict[str, Any]]:
    return _history(RECEIPT_ACTION)


def attempts_for_package(
    dissemination_package_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = delivery_attempt_history()
    if not dissemination_package_id:
        return rows
    return [
        row
        for row in rows
        if row.get("dissemination_package_id") == dissemination_package_id
    ]


def receipts_for_attempt(
    delivery_attempt_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = delivery_receipt_history()
    if not delivery_attempt_id:
        return rows
    return [row for row in rows if row.get("delivery_attempt_id") == delivery_attempt_id]


def find_delivery_attempt(delivery_attempt_id: str) -> dict[str, Any] | None:
    for item in delivery_attempt_history():
        if item.get("delivery_attempt_id") == delivery_attempt_id:
            return item
    return None


def find_delivery_receipt(delivery_receipt_id: str) -> dict[str, Any] | None:
    for item in delivery_receipt_history():
        if item.get("delivery_receipt_id") == delivery_receipt_id:
            return item
    return None


def latest_approved_decision(
    dissemination_package_id: str,
) -> dict[str, Any] | None:
    rows = decisions_for_package(dissemination_package_id)
    approved = [
        row
        for row in rows
        if row.get("status") == "approved_for_delivery_attempt"
        or row.get("result_status") == "approved_for_delivery_attempt"
    ]
    return approved[-1] if approved else None


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
            "ledger_record_id": row.id,
            "recorded_by": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _recipient_from_package(
    package: dict[str, Any],
    recipient_id: str,
) -> dict[str, Any] | None:
    manifest = package.get("package_manifest") or {}
    for recipient in manifest.get("recipients") or []:
        if recipient.get("recipient_id") == recipient_id:
            return recipient
    return None


def record_delivery_attempt(
    *,
    operator: str,
    dissemination_package_id: str,
    recipient_id: str,
    delivery_channel: str,
    endpoint_reference: str,
    attempt_result: str,
    transport_reference: str,
    reason: str,
    confirmed: bool,
    failure_code: str = "",
    failure_detail: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    dissemination_package_id = str(dissemination_package_id or "").strip()
    recipient_id = str(recipient_id or "").strip()
    delivery_channel = str(delivery_channel or "").strip().lower()
    endpoint_reference = str(endpoint_reference or "").strip()
    attempt_result = str(attempt_result or "").strip().lower()
    transport_reference = str(transport_reference or "").strip()
    reason = str(reason or "").strip()
    failure_code = str(failure_code or "").strip()
    failure_detail = str(failure_detail or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_delivery_attempt_confirmation_required")
    if attempt_result not in ALLOWED_ATTEMPT_RESULTS:
        return blocked("invalid_delivery_attempt_result")
    if not recipient_id:
        return blocked("recipient_id_required")
    if not delivery_channel:
        return blocked("delivery_channel_required")
    if not endpoint_reference:
        return blocked("opaque_endpoint_reference_required")
    if not transport_reference:
        return blocked("transport_reference_required")
    if not reason:
        return blocked("administrative_reason_required")
    if attempt_result == "failed" and not failure_code:
        return blocked("failure_code_required")

    package = find_dissemination_package(dissemination_package_id)
    if package is None:
        return blocked("dissemination_package_required")
    authorization = latest_approved_decision(dissemination_package_id)
    if authorization is None:
        return blocked("approved_authorization_decision_required")
    if authorization.get("dissemination_package_sha256") != package.get(
        "dissemination_package_sha256"
    ):
        return blocked("current_package_authorization_required")

    recipient = _recipient_from_package(package, recipient_id)
    if recipient is None:
        return blocked("authorized_package_recipient_required")
    if delivery_channel not in (recipient.get("allowed_channels") or []):
        return blocked("recipient_delivery_channel_not_allowed")

    binding = {
        "case_id": package.get("case_id"),
        "dissemination_package_id": dissemination_package_id,
        "dissemination_package_sha256": package.get(
            "dissemination_package_sha256"
        ),
        "authorization_decision_id": authorization.get(
            "authorization_decision_id"
        ),
        "authorization_decision_sha256": authorization.get(
            "authorization_decision_sha256"
        ),
        "recipient_id": recipient_id,
        "delivery_channel": delivery_channel,
        "endpoint_reference_sha256": _sha(endpoint_reference),
        "transport_reference": transport_reference,
    }
    content = {
        "event_type": ATTEMPT_ACTION,
        "case_id": package.get("case_id"),
        "dissemination_package_id": dissemination_package_id,
        "dissemination_package_sha256": package.get(
            "dissemination_package_sha256"
        ),
        "authorization_decision_id": authorization.get(
            "authorization_decision_id"
        ),
        "authorization_decision_sha256": authorization.get(
            "authorization_decision_sha256"
        ),
        "recipient_id": recipient_id,
        "delivery_channel": delivery_channel,
        "endpoint_reference_sha256": _sha(endpoint_reference),
        "transport_reference": transport_reference,
        "attempt_result": attempt_result,
        "failure_code": failure_code if attempt_result == "failed" else "",
        "failure_detail": failure_detail if attempt_result == "failed" else "",
        "reason": reason,
        "note": note,
        "attempt_binding": binding,
        "attempt_binding_sha256": _sha(binding),
        "transport_invoked_by_ledger": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "prior_attempt_mutated": False,
        "prior_receipt_mutated": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "delivery_attempt_id": f"delivery-attempt-{digest[:24]}",
        "delivery_attempt_sha256": digest,
    }
    if any(
        item.get("delivery_attempt_sha256") == digest
        for item in delivery_attempt_history()
    ):
        return blocked("delivery_attempt_already_exists")

    result = _record(
        actor=operator,
        action=ATTEMPT_ACTION,
        target_value=event["delivery_attempt_id"],
        event=event,
        ip_address=ip_address,
    )
    return {
        **result,
        "status": "delivery_attempt_recorded",
        "next_action": "record_delivery_receipt",
    }


def record_delivery_receipt(
    *,
    recorder: str,
    delivery_attempt_id: str,
    delivery_result: str,
    provider_message_id: str,
    transport_status: str,
    confirmed: bool,
    delivered_at: str = "",
    failure_code: str = "",
    failure_detail: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    delivery_attempt_id = str(delivery_attempt_id or "").strip()
    delivery_result = str(delivery_result or "").strip().lower()
    provider_message_id = str(provider_message_id or "").strip()
    transport_status = str(transport_status or "").strip()
    delivered_at = str(delivered_at or "").strip()
    failure_code = str(failure_code or "").strip()
    failure_detail = str(failure_detail or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_delivery_receipt_confirmation_required")
    if delivery_result not in ALLOWED_RECEIPT_RESULTS:
        return blocked("invalid_delivery_receipt_result")
    if not provider_message_id:
        return blocked("provider_message_id_required")
    if not transport_status:
        return blocked("transport_status_required")
    if delivery_result == "delivered" and not delivered_at:
        return blocked("delivered_at_required")
    if delivery_result == "failed" and not failure_code:
        return blocked("failure_code_required")

    attempt = find_delivery_attempt(delivery_attempt_id)
    if attempt is None:
        return blocked("delivery_attempt_required")
    if attempt.get("attempt_result") == "blocked":
        return blocked("accepted_or_failed_delivery_attempt_required")

    binding = {
        "delivery_attempt_id": delivery_attempt_id,
        "delivery_attempt_sha256": attempt.get("delivery_attempt_sha256"),
        "dissemination_package_id": attempt.get("dissemination_package_id"),
        "authorization_decision_id": attempt.get("authorization_decision_id"),
        "recipient_id": attempt.get("recipient_id"),
        "delivery_channel": attempt.get("delivery_channel"),
        "provider_message_id": provider_message_id,
    }
    content = {
        "event_type": RECEIPT_ACTION,
        "case_id": attempt.get("case_id"),
        "delivery_attempt_id": delivery_attempt_id,
        "delivery_attempt_sha256": attempt.get("delivery_attempt_sha256"),
        "dissemination_package_id": attempt.get("dissemination_package_id"),
        "authorization_decision_id": attempt.get("authorization_decision_id"),
        "recipient_id": attempt.get("recipient_id"),
        "delivery_channel": attempt.get("delivery_channel"),
        "delivery_result": delivery_result,
        "provider_message_id": provider_message_id,
        "transport_status": transport_status,
        "delivered_at": delivered_at if delivery_result == "delivered" else "",
        "failure_code": failure_code if delivery_result == "failed" else "",
        "failure_detail": failure_detail if delivery_result == "failed" else "",
        "note": note,
        "receipt_binding": binding,
        "receipt_binding_sha256": _sha(binding),
        "acknowledgement_required": delivery_result == "delivered",
        "transport_invoked_by_ledger": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "prior_attempt_mutated": False,
        "prior_receipt_mutated": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "delivery_receipt_id": f"delivery-receipt-{digest[:24]}",
        "delivery_receipt_sha256": digest,
    }
    if any(
        item.get("delivery_receipt_sha256") == digest
        for item in delivery_receipt_history()
    ):
        return blocked("delivery_receipt_already_exists")

    result = _record(
        actor=recorder,
        action=RECEIPT_ACTION,
        target_value=event["delivery_receipt_id"],
        event=event,
        ip_address=ip_address,
    )
    return {
        **result,
        "status": "delivery_receipt_recorded",
        "next_action": (
            "record_recipient_feedback"
            if delivery_result == "delivered"
            else "review_delivery_failure"
            if delivery_result == "failed"
            else "monitor_delivery_result"
        ),
    }
