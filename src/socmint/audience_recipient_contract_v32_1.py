from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_release_workspace_v22_0 import DEFAULT_CHANNELS

SCHEMA = "socmint.audience_recipient_contract.v32_1"
VERSION = "v32.1.0"
ACTION = "dissemination_audience_recipient_contract_recorded"
ALLOWED_AUDIENCE_TYPES = {
    "internal",
    "external_partner",
    "regulatory",
    "legal",
    "executive",
    "public",
}
ALLOWED_RECIPIENT_TYPES = {
    "person",
    "organization",
    "team",
    "system_account",
}
ALLOWED_CLASSIFICATIONS = {"public", "internal", "restricted"}
CLASSIFICATION_RANK = {"public": 0, "internal": 1, "restricted": 2}


def blocked(key: str, **details: Any) -> dict[str, Any]:
    blocker = {"key": key, **details}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [blocker],
        "authorization_granted": False,
        "package_assembly_performed": False,
        "transmission_performed": False,
        "published_revision_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }


def audience_contract_history() -> list[dict[str, Any]]:
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
                "contract_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def audience_contracts_for_case(
    case_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = audience_contract_history()
    if not case_id:
        return rows
    return [row for row in rows if row.get("case_id") == case_id]


def find_audience_contract(
    audience_contract_id: str,
) -> dict[str, Any] | None:
    for item in audience_contract_history():
        if item.get("audience_contract_id") == audience_contract_id:
            return item
    return None


def _normalize_recipient(
    value: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    recipient_id = str(value.get("recipient_id") or "").strip()
    display_name = str(value.get("display_name") or "").strip()
    organization = str(value.get("organization") or "").strip()
    role = str(value.get("role") or "").strip()
    recipient_type = (
        str(value.get("recipient_type") or "person").strip().lower()
    )
    purpose = str(value.get("dissemination_purpose") or "").strip()
    max_classification = (
        str(value.get("max_classification") or "internal").strip().lower()
    )
    raw_channels = value.get("allowed_channels")
    if not isinstance(raw_channels, list):
        return None, "recipient_allowed_channels_must_be_list"
    channels = sorted(
        {
            str(channel).strip().lower()
            for channel in raw_channels
            if str(channel).strip()
        }
    )

    if not recipient_id:
        return None, "recipient_id_required"
    if not display_name:
        return None, "recipient_display_name_required"
    if not organization:
        return None, "recipient_organization_required"
    if not role:
        return None, "recipient_role_required"
    if recipient_type not in ALLOWED_RECIPIENT_TYPES:
        return None, "invalid_recipient_type"
    if not purpose:
        return None, "recipient_dissemination_purpose_required"
    if max_classification not in ALLOWED_CLASSIFICATIONS:
        return None, "invalid_recipient_max_classification"
    if not channels:
        return None, "recipient_allowed_channel_required"
    invalid_channels = [
        channel for channel in channels if channel not in DEFAULT_CHANNELS
    ]
    if invalid_channels:
        return None, "recipient_channel_not_supported"

    return (
        {
            "recipient_id": recipient_id,
            "display_name": display_name,
            "organization": organization,
            "role": role,
            "recipient_type": recipient_type,
            "dissemination_purpose": purpose,
            "max_classification": max_classification,
            "allowed_channels": channels,
            "authorization_state": "not_authorized",
            "contact_reference_required_at_delivery": True,
        },
        None,
    )


def _record(
    actor: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
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
            "contract_record_id": row.id,
            "recorded_by": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_audience_recipient_contract(
    *,
    actor: str,
    case_id: str,
    audience_name: str,
    audience_type: str,
    dissemination_purpose: str,
    classification: str,
    recipients: list[dict[str, Any]],
    reason: str,
    confirmed: bool,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    audience_name = str(audience_name or "").strip()
    audience_type = str(audience_type or "").strip().lower()
    dissemination_purpose = str(dissemination_purpose or "").strip()
    classification = str(classification or "").strip().lower()
    reason = str(reason or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_contract_confirmation_required")
    if not case_id:
        return blocked("case_id_required")
    if not audience_name:
        return blocked("audience_name_required")
    if audience_type not in ALLOWED_AUDIENCE_TYPES:
        return blocked("invalid_audience_type")
    if not dissemination_purpose:
        return blocked("audience_dissemination_purpose_required")
    if classification not in ALLOWED_CLASSIFICATIONS:
        return blocked("invalid_audience_classification")
    if not reason:
        return blocked("administrative_reason_required")
    if not isinstance(recipients, list) or not recipients:
        return blocked("recipient_inventory_required")

    normalized: list[dict[str, Any]] = []
    for index, value in enumerate(recipients):
        if not isinstance(value, dict):
            return blocked("invalid_recipient_contract", recipient_index=index)
        recipient, error = _normalize_recipient(value)
        if error:
            return blocked(error, recipient_index=index)
        assert recipient is not None
        if (
            CLASSIFICATION_RANK[recipient["max_classification"]]
            < CLASSIFICATION_RANK[classification]
        ):
            return blocked(
                "recipient_classification_insufficient",
                recipient_index=index,
                recipient_id=recipient["recipient_id"],
            )
        normalized.append(recipient)

    recipient_ids = [item["recipient_id"] for item in normalized]
    if len(recipient_ids) != len(set(recipient_ids)):
        return blocked("duplicate_recipient_id")
    normalized.sort(key=lambda item: item["recipient_id"])

    audience_scope = {
        "case_id": case_id,
        "audience_name": audience_name,
        "audience_type": audience_type,
        "dissemination_purpose": dissemination_purpose,
        "classification": classification,
    }
    recipient_inventory = {
        "recipient_count": len(normalized),
        "recipients": normalized,
    }
    content = {
        "event_type": ACTION,
        "case_id": case_id,
        "audience_name": audience_name,
        "audience_type": audience_type,
        "dissemination_purpose": dissemination_purpose,
        "classification": classification,
        "contract_state": "proposed",
        "authorization_state": "not_authorized",
        "reason": reason,
        "note": note,
        "audience_scope": audience_scope,
        "audience_scope_sha256": _sha(audience_scope),
        "recipient_inventory": recipient_inventory,
        "recipient_inventory_sha256": _sha(recipient_inventory),
        "authorization_granted": False,
        "package_assembly_performed": False,
        "transmission_performed": False,
        "published_revision_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "audience_contract_id": f"audience-contract-{digest[:24]}",
        "audience_contract_sha256": digest,
    }
    if any(
        item.get("audience_contract_sha256") == digest
        for item in audience_contract_history()
    ):
        return blocked("audience_contract_already_exists")

    result = _record(
        actor,
        event["audience_contract_id"],
        event,
        ip_address,
    )
    return {
        **result,
        "status": "audience_contract_recorded",
        "next_action": "assemble_dissemination_package",
    }
