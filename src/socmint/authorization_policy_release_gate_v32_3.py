from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dissemination_package_v32_2 import find_dissemination_package

SCHEMA = "socmint.authorization_policy_release_gate.v32_3"
VERSION = "v32.3.0"
ACTION = "dissemination_authorization_policy_decision_recorded"
ALLOWED_DECISIONS = {"approve", "deny", "hold"}
ALLOWED_CLASSIFICATIONS = {"public", "internal", "restricted"}


def blocked(key: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key, **details}],
        "authorization_granted": False,
        "delivery_endpoint_resolved": False,
        "delivery_attempt_created": False,
        "transmission_performed": False,
        "package_mutated": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }


def authorization_decision_history() -> list[dict[str, Any]]:
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
                "decision_record_id": row.id,
                "reviewer": row.actor,
                "decided_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def decisions_for_package(
    dissemination_package_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = authorization_decision_history()
    if not dissemination_package_id:
        return rows
    return [
        row
        for row in rows
        if row.get("dissemination_package_id") == dissemination_package_id
    ]


def find_authorization_decision(
    authorization_decision_id: str,
) -> dict[str, Any] | None:
    for item in authorization_decision_history():
        if item.get("authorization_decision_id") == authorization_decision_id:
            return item
    return None


def _verify_package_integrity(package: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    source_binding = package.get("source_binding") or {}
    package_manifest = package.get("package_manifest") or {}
    package_payload = package.get("package_payload") or {}
    integrity = package.get("integrity") or {}

    if integrity.get("source_binding_sha256") != _sha(source_binding):
        blockers.append("source_binding_integrity_failed")
    if integrity.get("package_manifest_sha256") != _sha(package_manifest):
        blockers.append("package_manifest_integrity_failed")
    if integrity.get("package_payload_sha256") != _sha(package_payload):
        blockers.append("package_payload_integrity_failed")

    package_content = {
        key: value
        for key, value in package.items()
        if key
        not in {
            "schema",
            "version",
            "dissemination_package_id",
            "dissemination_package_sha256",
            "package_record_id",
            "assembled_by",
            "assembled_at",
            "status",
            "next_action",
        }
    }
    if package.get("dissemination_package_sha256") != _sha(package_content):
        blockers.append("dissemination_package_integrity_failed")
    return blockers


def _evaluate_policy(package: dict[str, Any]) -> dict[str, Any]:
    manifest = package.get("package_manifest") or {}
    recipients = list(manifest.get("recipients") or [])
    blockers: list[str] = []

    classification = str(manifest.get("classification") or "").lower()
    if classification not in ALLOWED_CLASSIFICATIONS:
        blockers.append("invalid_package_classification")
    if not str(manifest.get("dissemination_purpose") or "").strip():
        blockers.append("dissemination_purpose_required")
    if not recipients:
        blockers.append("recipient_manifest_required")

    for recipient in recipients:
        if recipient.get("authorization_state") != "not_authorized":
            blockers.append("recipient_pre_authorized_outside_gate")
        channels = recipient.get("allowed_channels") or []
        if not isinstance(channels, list) or not channels:
            blockers.append("recipient_allowed_channel_required")
        if recipient.get("delivery_endpoint_resolved") is not False:
            blockers.append("delivery_endpoint_must_remain_unresolved")

    return {
        "policy_status": "passed" if not blockers else "failed",
        "policy_blockers": sorted(set(blockers)),
        "classification": classification,
        "audience_type": manifest.get("audience_type"),
        "dissemination_purpose": manifest.get("dissemination_purpose"),
        "recipient_count": len(recipients),
        "section_count": int(manifest.get("section_count") or 0),
    }


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
            "decision_record_id": row.id,
            "reviewer": reviewer,
            "decided_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_authorization_policy_decision(
    *,
    reviewer: str,
    dissemination_package_id: str,
    decision: str,
    reason: str,
    confirmed: bool,
    policy_note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    dissemination_package_id = str(dissemination_package_id or "").strip()
    decision = str(decision or "").strip().lower()
    reason = str(reason or "").strip()
    policy_note = str(policy_note or "").strip()

    if decision not in ALLOWED_DECISIONS:
        return blocked("invalid_authorization_policy_decision")
    if confirmed is not True:
        return blocked("explicit_human_authorization_confirmation_required")
    if not reason:
        return blocked("administrative_reason_required")

    package = find_dissemination_package(dissemination_package_id)
    if package is None:
        return blocked("dissemination_package_required")
    if package.get("package_state") != "assembled_pending_authorization":
        return blocked("package_pending_authorization_required")
    if package.get("authorization_state") != "not_authorized":
        return blocked("unauthorized_package_required")

    integrity_blockers = _verify_package_integrity(package)
    if integrity_blockers:
        return blocked(
            "package_integrity_verification_failed",
            integrity_blockers=integrity_blockers,
        )

    policy = _evaluate_policy(package)
    if decision == "approve" and policy["policy_status"] != "passed":
        return blocked(
            "passing_authorization_policy_required",
            policy_blockers=policy["policy_blockers"],
        )

    result_status = {
        "approve": "approved_for_delivery_attempt",
        "deny": "release_denied",
        "hold": "release_held",
    }[decision]
    next_action = {
        "approve": "create_delivery_attempt",
        "deny": "revise_audience_or_package",
        "hold": "await_authorization_policy_decision",
    }[decision]
    authorization_granted = decision == "approve"

    binding = {
        "case_id": package.get("case_id"),
        "dissemination_package_id": dissemination_package_id,
        "dissemination_package_sha256": package.get(
            "dissemination_package_sha256"
        ),
        "published_revision_id": package.get("published_revision_id"),
        "published_revision_sha256": package.get("published_revision_sha256"),
        "audience_contract_id": package.get("audience_contract_id"),
        "audience_contract_sha256": package.get("audience_contract_sha256"),
        "source_binding_sha256": (package.get("integrity") or {}).get(
            "source_binding_sha256"
        ),
        "package_manifest_sha256": (package.get("integrity") or {}).get(
            "package_manifest_sha256"
        ),
        "package_payload_sha256": (package.get("integrity") or {}).get(
            "package_payload_sha256"
        ),
    }
    content = {
        "event_type": ACTION,
        "decision": decision,
        "result_status": result_status,
        "case_id": package.get("case_id"),
        "dissemination_package_id": dissemination_package_id,
        "dissemination_package_sha256": package.get(
            "dissemination_package_sha256"
        ),
        "published_revision_id": package.get("published_revision_id"),
        "audience_contract_id": package.get("audience_contract_id"),
        "policy_evaluation": policy,
        "policy_evaluation_sha256": _sha(policy),
        "authorization_binding": binding,
        "authorization_binding_sha256": _sha(binding),
        "reason": reason,
        "policy_note": policy_note,
        "human_confirmed": True,
        "authorization_state": result_status,
        "authorization_granted": authorization_granted,
        "delivery_eligibility": {
            "eligible": authorization_granted,
            "status": (
                "ready_for_delivery_attempt"
                if authorization_granted
                else "not_ready"
            ),
            "next_action": next_action,
        },
        "delivery_endpoint_resolved": False,
        "delivery_attempt_created": False,
        "transmission_performed": False,
        "package_mutated": False,
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "authorization_decision_id": f"authorization-decision-{digest[:24]}",
        "authorization_decision_sha256": digest,
    }
    if any(
        item.get("authorization_decision_sha256") == digest
        for item in authorization_decision_history()
    ):
        return blocked("authorization_policy_decision_already_exists")

    result = _record(
        reviewer,
        event["authorization_decision_id"],
        event,
        ip_address,
    )
    return {
        **result,
        "status": result_status,
        "next_action": next_action,
    }
