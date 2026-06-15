from __future__ import annotations

from typing import Any

from . import database
from .case_delivery_handoff_package_v15_1 import canonical_json, sha256_text
from .case_delivery_operations_v16_0 import build_case_delivery_operations_from_request
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .dossier_release_authorization_v22_1 import latest_release_authorization
from .dossier_release_preview_v22_2 import latest_release_preview

SCHEMA = "socmint.dossier_secure_distribution.v22_3"
VERSION = "v22.3.0"
ACTION = "case_dossier_secure_distribution"


def latest_secure_distribution(case_id: str) -> dict[str, Any] | None:
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
        details = _json_details(row)
        if "status" not in details:
            details["status"] = (
                "dispatch_recorded"
                if details.get("dispatch_result") == "accepted"
                else "dispatch_blocked"
            )
        return {
            **details,
            "distribution_record_id": row.id,
            "operator": row.actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _blockers(
    authorization: dict[str, Any] | None,
    preview: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if authorization is None:
        blockers.append({"key": "release_authorization_required"})
    if preview is None:
        blockers.append({"key": "acknowledged_release_preview_required"})
        return blockers
    if (
        preview.get("operator_acknowledged") is not True
        or preview.get("release_ready") is not True
    ):
        blockers.append({"key": "acknowledged_ready_preview_required"})
    if authorization:
        if preview.get("authorization_id") != authorization.get("authorization_id"):
            blockers.append({"key": "release_preview_authorization_mismatch"})
        if preview.get("export_package_id") != authorization.get("export_package_id"):
            blockers.append({"key": "release_preview_export_mismatch"})
        if preview.get("recipient_id") != authorization.get("recipient_id"):
            blockers.append({"key": "release_preview_recipient_mismatch"})
        if preview.get("delivery_channel") != authorization.get("delivery_channel"):
            blockers.append({"key": "release_preview_channel_mismatch"})
    return blockers


def build_secure_distribution_readiness(case_id: str) -> dict[str, Any]:
    authorization = latest_release_authorization(case_id)
    preview = latest_release_preview(case_id)
    blockers = _blockers(authorization, preview)
    ready = not blockers
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "ready_for_final_confirmation" if ready else "blocked",
        "ready": ready,
        "authorization": authorization,
        "release_preview": preview,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "final_operator_confirmation_required": True,
        "transport_invoked": False,
        "latest_distribution": latest_secure_distribution(case_id),
        "next_action": "confirm_secure_distribution" if ready else "resolve_distribution_blockers",
    }


def _execution_envelope_result(
    case_id: str,
    authorization: dict[str, Any],
    preview: dict[str, Any],
) -> dict[str, Any]:
    envelope_core = {
        "schema": "socmint.case_delivery_execution_envelope.v15_6",
        "version": "v15.6.0",
        "case_id": case_id,
        "delivery_id": f"dossier-release-{case_id}",
        "package_id": authorization.get("export_package_id"),
        "receipt_id": preview.get("preview_id"),
        "authorization_id": authorization.get("authorization_id"),
        "status": "ready_to_execute",
        "authorized_links": [],
        "manifest_file_count": len(preview.get("included_attachments") or []),
    }
    payload_sha256 = sha256_text(canonical_json(envelope_core))
    envelope = {
        **envelope_core,
        "payload_sha256": payload_sha256,
        "execution_id": sha256_text(
            canonical_json({**envelope_core, "payload_sha256": payload_sha256})
        ),
    }
    return {
        "schema": "socmint.case_delivery_execution_envelope.v15_6.result",
        "version": "v15.6.0",
        "case_id": case_id,
        "package_id": authorization.get("export_package_id"),
        "receipt_id": preview.get("preview_id"),
        "authorization_id": authorization.get("authorization_id"),
        "status": "ready_to_execute",
        "executable": True,
        "envelope": envelope,
        "authorization_result": {
            "status": "authorized",
            "authorized": True,
            "authorization": authorization.get("case_delivery_authorization") or {},
        },
        "blockers": [],
        "blocker_count": 0,
    }


def dispatch_secure_distribution(
    case_id: str,
    *,
    confirmed: bool,
    operator: str,
    note: str = "",
    ip_address: str | None = None,
    operations_builder=build_case_delivery_operations_from_request,
) -> dict[str, Any]:
    if confirmed is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "explicit_final_operator_confirmation_required"}],
            "transport_invoked": False,
        }

    readiness = build_secure_distribution_readiness(case_id)
    if not readiness["ready"]:
        return {
            **readiness,
            "status": "blocked",
            "transport_invoked": False,
        }

    authorization = readiness["authorization"]
    preview = readiness["release_preview"]
    dispatch_request = {
        "case_id": case_id,
        "export_package_id": authorization.get("export_package_id"),
        "export_package_sha256": authorization.get("export_package_sha256"),
        "authorization_id": authorization.get("authorization_id"),
        "authorization_sha256": authorization.get("authorization_sha256"),
        "preview_id": preview.get("preview_id"),
        "preview_sha256": preview.get("preview_sha256"),
        "recipient_id": authorization.get("recipient_id"),
        "delivery_channel": authorization.get("delivery_channel"),
        "operator": operator,
        "operator_confirmed": True,
        "note": str(note or "").strip(),
    }
    dispatch_request_sha256 = _sha(dispatch_request)
    operations_payload = {
        "execution_envelope_result": _execution_envelope_result(
            case_id, authorization, preview
        ),
        "events": [{
            "type": "dispatch_confirmed",
            "status": "recorded",
            "operator": operator,
            "detail": (
                f"Authorized dossier package {authorization.get('export_package_id')} "
                f"for recipient {authorization.get('recipient_id')} via "
                f"{authorization.get('delivery_channel')}"
            ),
        }],
    }
    operations_result = operations_builder(case_id, operations_payload)
    dispatched = (
        operations_result.get("state") == "dispatched"
        and operations_result.get("dispatchable") is True
    )
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "distribution_id": f"secure-distribution-{dispatch_request_sha256[:24]}",
        "dispatch_request": dispatch_request,
        "dispatch_request_sha256": dispatch_request_sha256,
        "case_delivery_operations_result": operations_result,
        "dispatch_result": "accepted" if dispatched else "blocked",
        "transport_invoked": True,
        "transport_engine": "existing_case_delivery_operations_v16_0",
        "source_export_mutated": False,
        "authorization_mutated": False,
        "preview_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=operator,
            action=ACTION,
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
        "status": "dispatch_recorded" if dispatched else "dispatch_blocked",
        "distribution_record_id": record_id,
        "operator": operator,
        "recorded_at": recorded_at,
        "next_action": (
            "monitor_delivery_result" if dispatched else "review_case_delivery_operations"
        ),
    }
