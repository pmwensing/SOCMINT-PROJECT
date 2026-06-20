from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_release_workspace_v22_0 import build_dossier_release_workspace

SCHEMA = "socmint.dossier_release_authorization.v22_1"
VERSION = "v22.1.0"
ACTION = "case_dossier_release_authorization"


def latest_release_authorization(case_id: str) -> dict[str, Any] | None:
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
            "authorization_record_id": row.id,
            "authorizer": row.actor,
            "authorized_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def authorize_dossier_release(
    case_id: str,
    *,
    recipient_id: str,
    delivery_channel: str,
    confirmed: bool,
    authorizer: str,
    note: str = "",
    recipients: list[dict[str, Any]] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "explicit_operator_confirmation_required"}],
            "transmission_performed": False,
        }

    preview = build_dossier_release_workspace(
        case_id,
        selected_recipient_id=recipient_id,
        selected_channel=delivery_channel,
        recipients=recipients,
    )
    if not preview.get("release_ready"):
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": preview.get("blockers")
            or [{"key": "release_configuration_not_ready"}],
            "release_preview": preview,
            "transmission_performed": False,
        }

    recipient = preview["selected_recipient"]
    export_package = preview["export_package"]
    content = {
        "case_id": case_id,
        "export_package_id": export_package.get("export_package_id"),
        "export_package_sha256": export_package.get("export_package_sha256"),
        "export_record_id": export_package.get("export_record_id"),
        "recipient_id": recipient["recipient_id"],
        "recipient_display_name": recipient["display_name"],
        "recipient_organization": recipient.get("organization"),
        "recipient_role": recipient.get("role"),
        "delivery_channel": delivery_channel,
        "operator_confirmed": True,
        "note": str(note or "").strip(),
    }
    authorization_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "authorization_id": f"release-auth-{authorization_sha256[:24]}",
        "authorization_sha256": authorization_sha256,
        "case_delivery_authorization": {
            "case_id": case_id,
            "export_package_id": content["export_package_id"],
            "export_package_sha256": content["export_package_sha256"],
            "recipient_id": content["recipient_id"],
            "delivery_channel": delivery_channel,
            "authorization_id": f"release-auth-{authorization_sha256[:24]}",
            "authorization_sha256": authorization_sha256,
            "authorized": True,
        },
        "transmission_performed": False,
        "source_export_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=authorizer,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        authorized_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "authorized",
        "authorization_record_id": record_id,
        "authorizer": authorizer,
        "authorized_at": authorized_at,
        "next_action": "open_case_delivery_workspace",
    }
