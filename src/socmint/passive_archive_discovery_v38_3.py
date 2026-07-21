from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .public_discovery_policy_gate_v38_2 import find_gate_decision

SCHEMA = "socmint.passive_archive_discovery.v38_3"
VERSION = "v38.3.0"
REGISTER_ACTION = "passive_archive_discovery_batch_registered"
PROVIDERS = ("common_crawl", "internet_archive")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "raw_response_recorded": False,
        "network_request_performed": False,
        "dns_lookup_performed": False,
        "archive_query_performed": False,
        "crawler_execution_performed": False,
        "browser_capture_performed": False,
        "artifact_created": False,
        "source_registered": False,
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


def _normalize_url(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        port_value = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    port = f":{port_value}" if port_value else ""
    path = parsed.path or "/"
    return urlunsplit(
        (parsed.scheme.lower(), f"{host}{port}", path, parsed.query, "")
    )


def _time(value: Any) -> str | None:
    raw = _required(value)
    if not raw:
        return None
    if len(raw) == 14 and raw.isdigit():
        try:
            parsed = datetime.strptime(raw, "%Y%m%d%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None
        return parsed.isoformat()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


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
    batch_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=REGISTER_ACTION,
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


def current_passive_batches() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        batch_id = str(event.get("passive_discovery_batch_id") or "")
        if batch_id:
            current[batch_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_passive_batch(batch_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_passive_batches()
            if item.get("passive_discovery_batch_id") == batch_id
        ),
        None,
    )


def _existing_candidate_keys() -> set[str]:
    return {
        str(candidate.get("duplicate_key_sha256"))
        for batch in current_passive_batches()
        for candidate in batch.get("candidates") or []
        if candidate.get("record_status") in {"accepted", "duplicate"}
        and candidate.get("duplicate_key_sha256")
    }


def _normalize_record(provider: str, raw: Any) -> dict[str, Any]:
    record = raw if isinstance(raw, dict) else {}
    if provider == "common_crawl":
        url = record.get("url")
        captured_at = record.get("timestamp")
        digest = record.get("digest")
        status_code = record.get("status")
        mime_type = record.get("mime") or record.get("mime-detected")
        archive_identifier = record.get("filename") or record.get("urlkey")
    else:
        url = record.get("original") or record.get("url")
        captured_at = record.get("timestamp")
        digest = record.get("digest")
        status_code = record.get("statuscode") or record.get("status")
        mime_type = record.get("mimetype") or record.get("mime")
        archive_identifier = (
            record.get("snapshot_id")
            or record.get("wayback_url")
            or record.get("urlkey")
        )

    normalized_url = _normalize_url(url)
    normalized_time = _time(captured_at)
    warnings = []
    if normalized_url is None:
        warnings.append("candidate_url_invalid")
    if normalized_time is None:
        warnings.append("capture_timestamp_invalid")
    digest = _required(digest) or None
    archive_identifier = _required(archive_identifier) or None
    if digest is None and archive_identifier is None:
        warnings.append("archive_digest_or_identifier_required")

    normalized = {
        "provider": provider,
        "candidate_url": normalized_url,
        "capture_timestamp": normalized_time,
        "digest": digest,
        "status_code": _required(status_code) or None,
        "mime_type": _required(mime_type) or None,
        "archive_identifier": archive_identifier,
        "normalization_warnings": sorted(set(warnings)),
    }
    identity = {
        "provider": provider,
        "candidate_url": normalized_url,
        "capture_timestamp": normalized_time,
        "digest": digest,
        "archive_identifier": archive_identifier,
    }
    duplicate_key = _sha(identity)
    candidate_digest = _sha(normalized)
    return {
        **normalized,
        "candidate_id": f"passive-archive-candidate-{candidate_digest[:24]}",
        "candidate_sha256": candidate_digest,
        "duplicate_key_sha256": duplicate_key,
    }


def register_passive_discovery_batch(
    *,
    actor: str,
    gate_decision_id: str,
    provider: str,
    index_version: str,
    query_reference: str,
    queried_at: str,
    adapter_name: str,
    adapter_version: str,
    response_records: list[dict[str, Any]] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    gate_decision_id = _required(gate_decision_id)
    provider = _required(provider)
    index_version = _required(index_version)
    query_reference = _required(query_reference)
    queried_at_normalized = _time(queried_at)
    adapter_name = _required(adapter_name)
    adapter_version = _required(adapter_version)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_passive_discovery_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not gate_decision_id:
        return blocked("public_discovery_gate_binding_required")
    if provider not in PROVIDERS:
        return blocked("passive_archive_provider_invalid")
    if not index_version or not query_reference:
        return blocked("archive_index_and_query_reference_required")
    if queried_at_normalized is None:
        return blocked("queried_at_invalid")
    if not adapter_name or not adapter_version:
        return blocked("adapter_identity_required")
    if not isinstance(response_records, list) or not response_records:
        return blocked("offline_response_records_required")
    if not reason:
        return blocked("administrative_reason_required")

    gate = find_gate_decision(gate_decision_id)
    if gate is None:
        return blocked("public_discovery_gate_decision_required")
    if gate.get("decision") != "allow" or gate.get(
        "passive_discovery_eligible"
    ) is not True:
        return blocked("allowing_passive_discovery_gate_required")
    if gate.get("live_network_eligible") is not False:
        return blocked("pre_live_network_gate_state_required")

    gate_binding = {
        "gate_decision_id": gate_decision_id,
        "gate_decision_event_sha256": gate.get("gate_decision_event_sha256"),
        "discovery_request_id": gate.get("discovery_request_id"),
        "request_binding_sha256": gate.get("request_binding_sha256"),
        "evaluation_sha256": gate.get("evaluation_sha256"),
        "decision": gate.get("decision"),
    }
    existing_keys = _existing_candidate_keys()
    seen_keys: set[str] = set()
    candidates = []
    for position, raw in enumerate(response_records, start=1):
        candidate = _normalize_record(provider, raw)
        duplicate_key = str(candidate.get("duplicate_key_sha256") or "")
        warnings = candidate.get("normalization_warnings") or []
        if warnings:
            record_status = "quarantined"
        elif duplicate_key in seen_keys or duplicate_key in existing_keys:
            record_status = "duplicate"
        else:
            record_status = "accepted"
            seen_keys.add(duplicate_key)
        candidates.append(
            {
                **candidate,
                "position": position,
                "record_status": record_status,
                "review_required": True,
                "evidence_status": "candidate_only",
                "artifact_created": False,
                "source_registered": False,
                "observation_created": False,
            }
        )

    counts = {
        "input": len(response_records),
        "accepted": sum(item["record_status"] == "accepted" for item in candidates),
        "duplicate": sum(item["record_status"] == "duplicate" for item in candidates),
        "quarantined": sum(
            item["record_status"] == "quarantined" for item in candidates
        ),
    }
    batch_definition = {
        "gate_binding": gate_binding,
        "provider": provider,
        "index_version": index_version,
        "query_reference": query_reference,
        "queried_at": queried_at_normalized,
        "adapter": {"name": adapter_name, "version": adapter_version},
        "candidate_sha256s": [item["candidate_sha256"] for item in candidates],
    }
    batch_id = f"passive-archive-batch-{_sha(batch_definition)[:24]}"
    existing = find_passive_batch(batch_id)
    if existing is not None:
        return {
            **existing,
            "status": "passive_archive_discovery_batch_reused",
            "idempotent_replay": True,
            "next_action": "review_passive_archive_candidates",
        }

    content = {
        "event_type": REGISTER_ACTION,
        "passive_discovery_batch_id": batch_id,
        "gate_decision_id": gate_decision_id,
        "gate_binding": gate_binding,
        "gate_binding_sha256": _sha(gate_binding),
        "provider": provider,
        "index_version": index_version,
        "query_reference": query_reference,
        "queried_at": queried_at_normalized,
        "adapter": {"name": adapter_name, "version": adapter_version},
        "batch_definition_sha256": _sha(batch_definition),
        "candidates": candidates,
        "counts": counts,
        "reason": reason,
        "raw_response_recorded": False,
        "offline_response_consumed": True,
        "network_request_performed": False,
        "dns_lookup_performed": False,
        "archive_query_performed": False,
        "crawler_execution_performed": False,
        "browser_capture_performed": False,
        "artifact_created": False,
        "source_registered": False,
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
        "passive_discovery_event_id": f"passive-archive-event-{digest[:24]}",
        "passive_discovery_event_sha256": digest,
    }
    result = _record(actor, batch_id, event, ip_address)
    return {
        **result,
        "status": "passive_archive_discovery_batch_registered",
        "idempotent_replay": False,
        "next_action": "review_passive_archive_candidates",
    }
