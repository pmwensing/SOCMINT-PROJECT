from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .dossier_secure_distribution_v22_3 import latest_secure_distribution

SCHEMA = "socmint.dossier_delivery_receipt.v22_4"
VERSION = "v22.4.0"
RECEIPT_ACTION = "case_dossier_delivery_receipt"
ACK_ACTION = "case_dossier_recipient_acknowledgement"
ALLOWED_RESULTS = {"delivered", "failed"}


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


def latest_delivery_receipt(case_id: str) -> dict[str, Any] | None:
    value = _latest(case_id, RECEIPT_ACTION)
    if value is not None:
        value["delivery_receipt_record_id"] = value.pop("record_id")
    return value


def latest_recipient_acknowledgement(case_id: str) -> dict[str, Any] | None:
    value = _latest(case_id, ACK_ACTION)
    if value is not None:
        value["acknowledgement_record_id"] = value.pop("record_id")
    return value


def build_delivery_receipt_state(case_id: str) -> dict[str, Any]:
    distribution = latest_secure_distribution(case_id)
    receipt = latest_delivery_receipt(case_id)
    acknowledgement = latest_recipient_acknowledgement(case_id)
    blockers: list[dict[str, str]] = []
    if distribution is None:
        blockers.append({"key": "secure_distribution_required"})
    elif distribution.get("status") != "dispatch_recorded":
        blockers.append({"key": "accepted_distribution_required"})

    receipt_matches = bool(
        distribution
        and receipt
        and receipt.get("distribution_id") == distribution.get("distribution_id")
        and receipt.get("dispatch_request_sha256")
        == distribution.get("dispatch_request_sha256")
    )
    delivered = receipt_matches and receipt.get("delivery_result") == "delivered"
    acknowledgement_matches = bool(
        acknowledgement
        and receipt
        and acknowledgement.get("delivery_receipt_id") == receipt.get("delivery_receipt_id")
        and acknowledgement.get("delivery_receipt_sha256")
        == receipt.get("delivery_receipt_sha256")
    )
    acknowledgement_outstanding = delivered and not acknowledgement_matches

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "blocked" if blockers else "tracking",
        "distribution": distribution,
        "latest_delivery_receipt": receipt,
        "latest_recipient_acknowledgement": acknowledgement,
        "receipt_matches_distribution": receipt_matches,
        "delivery_succeeded": delivered,
        "acknowledgement_received": acknowledgement_matches,
        "acknowledgement_outstanding": acknowledgement_outstanding,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "dispatch_record_mutated": False,
        "next_action": (
            "record_delivery_receipt"
            if not blockers and receipt is None
            else "record_recipient_acknowledgement"
            if acknowledgement_outstanding
            else "review_delivery_failure"
            if receipt_matches and receipt.get("delivery_result") == "failed"
            else "delivery_handoff_complete"
            if acknowledgement_matches
            else "resolve_delivery_receipt_state"
        ),
    }


def record_delivery_receipt(
    case_id: str,
    *,
    delivery_result: str,
    recorder: str,
    provider_message_id: str = "",
    transport_status: str = "",
    failure_code: str = "",
    failure_detail: str = "",
    delivered_at: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    result = str(delivery_result or "").strip().lower()
    if result not in ALLOWED_RESULTS:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "invalid_delivery_result"}],
            "dispatch_record_mutated": False,
        }
    distribution = latest_secure_distribution(case_id)
    if distribution is None or distribution.get("status") != "dispatch_recorded":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "accepted_distribution_required"}],
            "dispatch_record_mutated": False,
        }

    request = distribution.get("dispatch_request") or {}
    content = {
        "case_id": case_id,
        "distribution_id": distribution.get("distribution_id"),
        "distribution_record_id": distribution.get("distribution_record_id"),
        "dispatch_request_sha256": distribution.get("dispatch_request_sha256"),
        "export_package_id": request.get("export_package_id"),
        "recipient_id": request.get("recipient_id"),
        "delivery_channel": request.get("delivery_channel"),
        "delivery_result": result,
        "provider_message_id": str(provider_message_id or "").strip(),
        "transport_status": str(transport_status or "").strip(),
        "failure_code": str(failure_code or "").strip() if result == "failed" else "",
        "failure_detail": str(failure_detail or "").strip() if result == "failed" else "",
        "delivered_at": str(delivered_at or "").strip() if result == "delivered" else "",
        "note": str(note or "").strip(),
    }
    receipt_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "delivery_receipt_id": f"delivery-receipt-{receipt_sha256[:24]}",
        "delivery_receipt_sha256": receipt_sha256,
        "acknowledgement_required": result == "delivered",
        "dispatch_record_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=recorder,
            action=RECEIPT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        recorded_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "delivery_recorded",
        "delivery_receipt_record_id": record_id,
        "recorded_by": recorder,
        "recorded_at": recorded_at,
        "next_action": (
            "record_recipient_acknowledgement"
            if result == "delivered"
            else "review_delivery_failure"
        ),
    }


def record_recipient_acknowledgement(
    case_id: str,
    *,
    acknowledged: bool,
    recorder: str,
    recipient_name: str = "",
    acknowledgement_method: str = "",
    acknowledged_at: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if acknowledged is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "explicit_recipient_acknowledgement_required"}],
            "dispatch_record_mutated": False,
        }
    receipt = latest_delivery_receipt(case_id)
    if receipt is None or receipt.get("delivery_result") != "delivered":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "successful_delivery_receipt_required"}],
            "dispatch_record_mutated": False,
        }

    content = {
        "case_id": case_id,
        "delivery_receipt_id": receipt.get("delivery_receipt_id"),
        "delivery_receipt_sha256": receipt.get("delivery_receipt_sha256"),
        "distribution_id": receipt.get("distribution_id"),
        "export_package_id": receipt.get("export_package_id"),
        "recipient_id": receipt.get("recipient_id"),
        "recipient_name": str(recipient_name or "").strip(),
        "acknowledgement_method": str(acknowledgement_method or "").strip(),
        "acknowledged_at": str(acknowledged_at or "").strip(),
        "recipient_acknowledged": True,
        "note": str(note or "").strip(),
    }
    ack_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "acknowledgement_id": f"recipient-ack-{ack_sha256[:24]}",
        "acknowledgement_sha256": ack_sha256,
        "dispatch_record_mutated": False,
        "delivery_receipt_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=recorder,
            action=ACK_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        recorded_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "acknowledgement_recorded",
        "acknowledgement_record_id": record_id,
        "recorded_by": recorder,
        "recorded_at": recorded_at,
        "next_action": "delivery_handoff_complete",
    }
