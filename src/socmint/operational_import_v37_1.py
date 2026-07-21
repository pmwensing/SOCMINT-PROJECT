from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import find_artifact

SCHEMA = "socmint.operational_import.v37_1"
VERSION = "v37.1.0"
REGISTER_ACTION = "operational_import_envelope_registered"
EXPORT_FORMATS = ("json", "jsonl", "ndjson", "csv", "html")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_FILENAME = re.compile(r"^[^\x00-\x1f\\/]+$")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "raw_payload_recorded": False,
        "connector_execution_performed": False,
        "hidden_collection_performed": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }


def _required(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_required(item) for item in value if _required(item)})


def _time(value: Any) -> datetime | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=REGISTER_ACTION)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    actor: str,
    import_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=REGISTER_ACTION,
            target_value=import_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "audit_record_id": row.id,
            "actor": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_imports() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        import_id = str(event.get("operational_import_id") or "")
        if import_id:
            current[import_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_import(import_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_imports()
            if item.get("operational_import_id") == import_id
        ),
        None,
    )


def _artifact_binding(
    artifact: dict[str, Any], case_id: str, content_sha256: str
) -> tuple[dict[str, Any] | None, str | None]:
    if artifact.get("artifact_state") != "accepted":
        return None, "accepted_evidence_artifact_required"
    contract = artifact.get("contract_binding") or {}
    if not isinstance(contract, dict):
        return None, "artifact_contract_binding_required"
    if str(contract.get("case_id") or "") != case_id:
        return None, "import_case_artifact_binding_mismatch"
    if str(artifact.get("content_sha256") or "").lower() != content_sha256:
        return None, "import_content_artifact_hash_mismatch"
    latest = (artifact.get("state_history") or [artifact])[-1]
    return (
        {
            "artifact_id": artifact.get("artifact_id"),
            "artifact_event_sha256": latest.get("artifact_event_sha256"),
            "content_sha256": artifact.get("content_sha256"),
            "acquisition_sha256": artifact.get("acquisition_sha256"),
            "collection_job_id": artifact.get("collection_job_id"),
            "case_id": contract.get("case_id"),
            "entity_id": contract.get("entity_id"),
            "source_id": contract.get("source_id"),
        },
        None,
    )


def register_import_envelope(
    *,
    actor: str,
    case_id: str,
    purpose: str,
    artifact_id: str,
    content_sha256: str,
    original_filename: str,
    media_type: str,
    export_format: str,
    tool_name: str,
    tool_version: str,
    adapter_name: str,
    adapter_version: str,
    exported_at: str,
    imported_at: str,
    declared_record_count: int,
    source_references: list[str] | None,
    collection_context: dict[str, Any] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    purpose = _required(purpose)
    artifact_id = _required(artifact_id)
    content_sha256 = _required(content_sha256).lower()
    original_filename = _required(original_filename)
    media_type = _required(media_type)
    export_format = _required(export_format).lower()
    tool_name = _required(tool_name)
    tool_version = _required(tool_version)
    adapter_name = _required(adapter_name)
    adapter_version = _required(adapter_version)
    source_references = _string_list(source_references)
    context = collection_context if isinstance(collection_context, dict) else None
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_import_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id or not purpose:
        return blocked("case_and_purpose_required")
    if not artifact_id:
        return blocked("accepted_artifact_binding_required")
    if not _SHA256.fullmatch(content_sha256):
        return blocked("content_sha256_invalid")
    if (
        not original_filename
        or PurePath(original_filename).name != original_filename
        or not _SAFE_FILENAME.fullmatch(original_filename)
    ):
        return blocked("original_filename_invalid")
    if not media_type:
        return blocked("media_type_required")
    if export_format not in EXPORT_FORMATS:
        return blocked("export_format_invalid")
    if not all((tool_name, tool_version, adapter_name, adapter_version)):
        return blocked("tool_and_adapter_identity_required")
    exported = _time(exported_at)
    imported = _time(imported_at)
    if exported is None or imported is None:
        return blocked("exported_and_imported_times_required")
    if imported < exported:
        return blocked("import_time_precedes_export_time")
    try:
        declared_record_count = int(declared_record_count)
    except (TypeError, ValueError):
        return blocked("declared_record_count_invalid")
    if declared_record_count < 0:
        return blocked("declared_record_count_invalid")
    if context is None:
        return blocked("collection_context_object_required")
    if not reason:
        return blocked("administrative_reason_required")

    artifact = find_artifact(artifact_id)
    if artifact is None:
        return blocked("evidence_artifact_required")
    artifact_binding, binding_error = _artifact_binding(
        artifact, case_id, content_sha256
    )
    if binding_error:
        return blocked(binding_error)
    assert artifact_binding is not None

    envelope = {
        "case_id": case_id,
        "purpose": purpose,
        "artifact_binding": artifact_binding,
        "artifact_binding_sha256": _sha(artifact_binding),
        "original_filename": original_filename,
        "media_type": media_type,
        "export_format": export_format,
        "tool": {"name": tool_name, "version": tool_version},
        "adapter": {"name": adapter_name, "version": adapter_version},
        "exported_at": exported.isoformat(),
        "imported_at": imported.isoformat(),
        "declared_record_count": declared_record_count,
        "source_references": source_references,
        "collection_context": context,
    }
    identity = {
        "case_id": case_id,
        "artifact_id": artifact_id,
        "content_sha256": content_sha256,
        "export_format": export_format,
        "tool": envelope["tool"],
        "adapter": envelope["adapter"],
        "exported_at": envelope["exported_at"],
    }
    import_id = f"operational-import-{_sha(identity)[:24]}"
    existing = find_import(import_id)
    if existing is not None:
        return {
            **existing,
            "status": "operational_import_reused",
            "idempotent_replay": True,
            "next_action": "stage_import_records",
        }

    content = {
        "event_type": REGISTER_ACTION,
        "operational_import_id": import_id,
        "envelope": envelope,
        "envelope_sha256": _sha(envelope),
        "rerun_key_sha256": _sha(identity),
        "record_counts": {
            "declared": declared_record_count,
            "staged": 0,
            "accepted": 0,
            "quarantined": 0,
            "duplicate": 0,
            "rejected": 0,
        },
        "reason": reason,
        "raw_payload_recorded": False,
        "connector_execution_performed": False,
        "hidden_collection_performed": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "operational_import_event_id": f"operational-import-event-{digest[:24]}",
        "operational_import_event_sha256": digest,
    }
    result = _record(actor, import_id, event, ip_address)
    return {
        **result,
        "status": "operational_import_registered",
        "idempotent_replay": False,
        "next_action": "stage_import_records",
    }
