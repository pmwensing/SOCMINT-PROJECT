from __future__ import annotations

from typing import Any

from . import database
from .audience_recipient_contract_v32_1 import find_audience_contract
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .immutable_published_revision_v31_5 import current_published_revisions
from .publication_supersession_v31_6 import revision_history_for_case

SCHEMA = "socmint.dissemination_package.v32_2"
VERSION = "v32.2.0"
ACTION = "dissemination_package_assembled"


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
        "published_revision_mutated": False,
        "audience_contract_mutated": False,
        "delivery_history_mutated": False,
        "contact_secret_stored": False,
    }


def dissemination_package_history() -> list[dict[str, Any]]:
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
                "package_record_id": row.id,
                "assembled_by": row.actor,
                "assembled_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def dissemination_packages_for_case(
    case_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = dissemination_package_history()
    if not case_id:
        return rows
    return [row for row in rows if row.get("case_id") == case_id]


def find_dissemination_package(
    dissemination_package_id: str,
) -> dict[str, Any] | None:
    for item in dissemination_package_history():
        if item.get("dissemination_package_id") == dissemination_package_id:
            return item
    return None


def find_published_revision(
    published_revision_id: str,
) -> dict[str, Any] | None:
    for item in current_published_revisions():
        if item.get("published_revision_id") == published_revision_id:
            return item
    return None


def _active_revision_ids(case_id: str) -> set[str]:
    history = revision_history_for_case(case_id)
    return {
        str(value)
        for value in history.get("active_revision_ids") or []
        if str(value)
    }


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
            "package_record_id": row.id,
            "assembled_by": actor,
            "assembled_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def assemble_dissemination_package(
    *,
    actor: str,
    published_revision_id: str,
    audience_contract_id: str,
    package_label: str,
    reason: str,
    confirmed: bool,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    published_revision_id = str(published_revision_id or "").strip()
    audience_contract_id = str(audience_contract_id or "").strip()
    package_label = str(package_label or "").strip()
    reason = str(reason or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_package_assembly_confirmation_required")
    if not package_label:
        return blocked("package_label_required")
    if not reason:
        return blocked("administrative_reason_required")

    publication = find_published_revision(published_revision_id)
    if publication is None:
        return blocked("immutable_published_revision_required")
    if publication.get("immutable") is not True:
        return blocked("immutable_published_revision_required")
    if publication.get("revision_state") != "published":
        return blocked("published_revision_state_required")

    audience = find_audience_contract(audience_contract_id)
    if audience is None:
        return blocked("audience_recipient_contract_required")
    if audience.get("contract_state") != "proposed":
        return blocked("proposed_audience_contract_required")
    if audience.get("authorization_state") != "not_authorized":
        return blocked("unauthorized_audience_contract_required")

    case_id = str(publication.get("case_id") or "")
    if not case_id or audience.get("case_id") != case_id:
        return blocked("publication_audience_case_mismatch")
    if published_revision_id not in _active_revision_ids(case_id):
        return blocked("active_published_revision_required")

    published_content = publication.get("published_content") or {}
    sections = list(published_content.get("sections") or [])
    recipient_inventory = audience.get("recipient_inventory") or {}
    recipients = list(recipient_inventory.get("recipients") or [])
    if not recipients:
        return blocked("recipient_inventory_required")

    recipient_manifest = [
        {
            "recipient_id": recipient.get("recipient_id"),
            "display_name": recipient.get("display_name"),
            "organization": recipient.get("organization"),
            "role": recipient.get("role"),
            "recipient_type": recipient.get("recipient_type"),
            "dissemination_purpose": recipient.get("dissemination_purpose"),
            "max_classification": recipient.get("max_classification"),
            "allowed_channels": sorted(recipient.get("allowed_channels") or []),
            "authorization_state": "not_authorized",
            "delivery_endpoint_resolved": False,
        }
        for recipient in recipients
    ]
    recipient_manifest.sort(key=lambda item: str(item.get("recipient_id") or ""))

    section_manifest = [
        {
            "section_id": section.get("section_id"),
            "title": section.get("title"),
            "position": section.get("position"),
            "section_sha256": _sha(section),
        }
        for section in sections
    ]
    section_manifest.sort(
        key=lambda item: (
            int(item.get("position") or 0),
            str(item.get("section_id") or ""),
        )
    )

    source_binding = {
        "case_id": case_id,
        "published_revision_id": published_revision_id,
        "published_revision_sha256": publication.get("published_revision_sha256"),
        "published_content_sha256": (
            publication.get("integrity") or {}
        ).get("published_content_sha256"),
        "audience_contract_id": audience_contract_id,
        "audience_contract_sha256": audience.get("audience_contract_sha256"),
        "audience_scope_sha256": audience.get("audience_scope_sha256"),
        "recipient_inventory_sha256": audience.get("recipient_inventory_sha256"),
    }
    package_manifest = {
        "format": "socmint-json",
        "media_type": "application/json",
        "classification": audience.get("classification"),
        "audience_name": audience.get("audience_name"),
        "audience_type": audience.get("audience_type"),
        "dissemination_purpose": audience.get("dissemination_purpose"),
        "section_count": len(section_manifest),
        "recipient_count": len(recipient_manifest),
        "sections": section_manifest,
        "recipients": recipient_manifest,
    }
    package_payload = {
        "publication_label": publication.get("publication_label"),
        "published_content": published_content,
        "publication_metadata": publication.get("metadata") or {},
        "publication_provenance": publication.get("provenance") or {},
    }
    integrity = {
        "source_binding_sha256": _sha(source_binding),
        "package_manifest_sha256": _sha(package_manifest),
        "package_payload_sha256": _sha(package_payload),
    }
    content = {
        "event_type": ACTION,
        "case_id": case_id,
        "package_label": package_label,
        "package_state": "assembled_pending_authorization",
        "reason": reason,
        "note": note,
        "published_revision_id": published_revision_id,
        "published_revision_sha256": publication.get("published_revision_sha256"),
        "audience_contract_id": audience_contract_id,
        "audience_contract_sha256": audience.get("audience_contract_sha256"),
        "source_binding": source_binding,
        "package_manifest": package_manifest,
        "package_payload": package_payload,
        "integrity": integrity,
        "authorization_state": "not_authorized",
        "authorization_granted": False,
        "delivery_endpoint_resolved": False,
        "delivery_attempt_created": False,
        "transmission_performed": False,
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
        "dissemination_package_id": f"dissemination-package-{digest[:24]}",
        "dissemination_package_sha256": digest,
    }
    if any(
        item.get("dissemination_package_sha256") == digest
        for item in dissemination_package_history()
    ):
        return blocked("dissemination_package_already_exists")

    result = _record(
        actor,
        event["dissemination_package_id"],
        event,
        ip_address,
    )
    return {
        **result,
        "status": "dissemination_package_assembled",
        "next_action": "review_authorization_policy_and_release_gate",
    }
