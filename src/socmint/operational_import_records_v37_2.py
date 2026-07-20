from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .operational_import_v37_1 import find_import

SCHEMA = "socmint.operational_import_records.v37_2"
VERSION = "v37.2.0"
STAGE_ACTION = "operational_import_records_staged"
MAX_BATCH_RECORDS = 1000
INITIAL_STATES = ("accepted", "quarantined", "duplicate")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "raw_export_payload_recorded": False,
        "connector_execution_performed": False,
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
            .filter_by(action=STAGE_ACTION)
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
    batch_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=STAGE_ACTION,
            target_value=batch_id,
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


def current_batches() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        batch_id = str(event.get("staged_record_batch_id") or "")
        if batch_id:
            current[batch_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def current_staged_records(import_id: str | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for batch in current_batches():
        if import_id and batch.get("operational_import_id") != import_id:
            continue
        for item in batch.get("records") or []:
            if isinstance(item, dict):
                records.append(
                    {
                        **item,
                        "staged_record_batch_id": batch.get("staged_record_batch_id"),
                        "batch_event_sha256": batch.get("batch_event_sha256"),
                        "batch_recorded_at": batch.get("recorded_at"),
                    }
                )
    return sorted(
        records,
        key=lambda item: str(item.get("staged_record_id") or ""),
    )


def find_staged_record(staged_record_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_staged_records()
            if item.get("staged_record_id") == staged_record_id
        ),
        None,
    )


def find_batch(batch_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_batches()
            if item.get("staged_record_batch_id") == batch_id
        ),
        None,
    )


def _normalize_record(import_id: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source_record_id = _required(value.get("source_record_id"))
    record_type = _required(value.get("record_type"))
    observed = _time(value.get("observed_at"))
    raw_value = value.get("raw_value")
    normalized_value = value.get("normalized_value")
    context = value.get("context")
    source_references = _string_list(value.get("source_references"))
    warnings = _string_list(value.get("warnings"))
    if not source_record_id or not record_type or observed is None:
        return None
    if raw_value in (None, "") or normalized_value in (None, ""):
        return None
    if not isinstance(context, dict):
        return None
    try:
        confidence = float(value.get("extraction_confidence"))
    except (TypeError, ValueError):
        return None
    if confidence < 0.0 or confidence > 1.0:
        return None
    record = {
        "source_record_id": source_record_id,
        "record_type": record_type,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "observed_at": observed.isoformat(),
        "extraction_confidence": confidence,
        "context": context,
        "source_references": source_references,
        "warnings": warnings,
    }
    record_sha256 = _sha(
        {
            "operational_import_id": import_id,
            "record": record,
        }
    )
    return {
        **record,
        "record_sha256": record_sha256,
        "staged_record_id": f"staged-import-record-{record_sha256[:24]}",
    }


def stage_import_records(
    *,
    actor: str,
    import_id: str,
    records: list[dict[str, Any]] | None,
    adapter_diagnostics: dict[str, Any] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    import_id = _required(import_id)
    reason = _required(reason)
    diagnostics = adapter_diagnostics if isinstance(adapter_diagnostics, dict) else None
    if confirmed is not True:
        return blocked("explicit_record_staging_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not import_id:
        return blocked("operational_import_id_required")
    parent = find_import(import_id)
    if parent is None:
        return blocked("operational_import_required")
    if not isinstance(records, list) or not records:
        return blocked("import_records_required")
    if len(records) > MAX_BATCH_RECORDS:
        return blocked("import_record_batch_limit_exceeded")
    if diagnostics is None:
        return blocked("adapter_diagnostics_object_required")
    if diagnostics.get("network_access_performed") is True:
        return blocked("networked_adapter_output_not_allowed")
    if diagnostics.get("collection_performed") is True:
        return blocked("collection_adapter_output_not_allowed")
    if not reason:
        return blocked("administrative_reason_required")

    normalized = [_normalize_record(import_id, item) for item in records]
    if any(item is None for item in normalized):
        return blocked("import_record_contract_invalid")
    normalized_records = [item for item in normalized if item is not None]

    existing_by_hash = {
        str(item.get("record_sha256") or ""): item
        for item in current_staged_records()
        if item.get("record_sha256")
    }
    seen_in_batch: dict[str, str] = {}
    staged: list[dict[str, Any]] = []
    counts = {state: 0 for state in INITIAL_STATES}
    for item in normalized_records:
        digest = str(item["record_sha256"])
        duplicate_of = None
        if digest in existing_by_hash:
            duplicate_of = existing_by_hash[digest].get("staged_record_id")
        elif digest in seen_in_batch:
            duplicate_of = seen_in_batch[digest]
        if duplicate_of:
            state = "duplicate"
        elif item["warnings"] or item["extraction_confidence"] < 0.5:
            state = "quarantined"
        else:
            state = "accepted"
        seen_in_batch.setdefault(digest, str(item["staged_record_id"]))
        counts[state] += 1
        staged.append(
            {
                **item,
                "initial_state": state,
                "duplicate_of_staged_record_id": duplicate_of,
                "observation_created": False,
                "claim_support_allowed": state == "accepted",
            }
        )

    import_binding = {
        "operational_import_id": import_id,
        "operational_import_event_sha256": parent.get(
            "operational_import_event_sha256"
        ),
        "envelope_sha256": parent.get("envelope_sha256"),
        "rerun_key_sha256": parent.get("rerun_key_sha256"),
    }
    batch_identity = {
        "import_binding_sha256": _sha(import_binding),
        "record_hashes": [item["record_sha256"] for item in staged],
        "adapter_diagnostics": diagnostics,
    }
    batch_id = f"staged-import-batch-{_sha(batch_identity)[:24]}"
    existing_batch = find_batch(batch_id)
    if existing_batch is not None:
        return {
            **existing_batch,
            "status": "staged_record_batch_reused",
            "idempotent_replay": True,
            "next_action": "review_quarantine_and_scope",
        }

    content = {
        "event_type": STAGE_ACTION,
        "staged_record_batch_id": batch_id,
        "operational_import_id": import_id,
        "import_binding": import_binding,
        "import_binding_sha256": _sha(import_binding),
        "adapter_diagnostics": diagnostics,
        "adapter_diagnostics_sha256": _sha(diagnostics),
        "records": staged,
        "record_counts": {
            "submitted": len(records),
            "staged": len(staged),
            **counts,
            "rejected": 0,
        },
        "reason": reason,
        "raw_export_payload_recorded": False,
        "connector_execution_performed": False,
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
        "batch_event_id": f"staged-import-batch-event-{digest[:24]}",
        "batch_event_sha256": digest,
    }
    result = _record(actor, batch_id, event, ip_address)
    return {
        **result,
        "status": "import_records_staged",
        "idempotent_replay": False,
        "next_action": "review_quarantine_and_scope",
    }
