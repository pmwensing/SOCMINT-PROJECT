from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .evidence_ingestion_v29_4 import find_artifact, register_artifact
from .operational_import_v37_1 import register_import_envelope
from .passive_archive_discovery_v38_3 import find_passive_batch
from .public_discovery_policy_gate_v38_2 import find_gate_decision
from .public_discovery_request_v38_1 import find_discovery_request
from .source_registry_v36_1 import register_source

SCHEMA = "socmint.synthetic_capture_provenance.v38_4"
VERSION = "v38.4.0"
PREPARE_ACTION = "synthetic_capture_artifacts_prepared"
FINALIZE_ACTION = "synthetic_capture_provenance_finalized"
ACTIONS = (PREPARE_ACTION, FINALIZE_ACTION)
REQUIRED_ROLES = (
    "primary_html",
    "public_document_pdf",
    "archive_capture",
    "screenshot",
)
ROLE_MEDIA_TYPES = {
    "primary_html": {"text/html"},
    "public_document_pdf": {"application/pdf"},
    "archive_capture": {
        "application/warc",
        "application/wacz",
        "application/octet-stream",
    },
    "screenshot": {"image/png", "image/jpeg"},
}
SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}
_SAFE_FILENAME = re.compile(r"^[^\x00-\x1f\\/]+$")


def blocked(key: str, **details: Any) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "raw_content_recorded": False,
        "network_request_performed": False,
        "dns_lookup_performed": False,
        "archive_query_performed": False,
        "crawler_execution_performed": False,
        "browser_capture_performed": False,
        "observation_created": False,
        "truth_assigned": False,
        "entity_merged": False,
        "claim_approved": False,
        "dossier_mutated": False,
        "export_created": False,
        "published": False,
    }
    if details:
        result["details"] = details
    return result


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
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat()


def _content_bytes(value: Any) -> bytes | None:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return None


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.action.in_(ACTIONS))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "audit_record_id": row.id,
                "actor": row.actor,
                "source_action": row.action,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str,
    actor: str,
    target: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target,
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
            "source_action": action,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_synthetic_captures() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        capture_id = str(event.get("synthetic_capture_id") or "")
        if not capture_id:
            continue
        if event.get("event_type") == PREPARE_ACTION:
            current[capture_id] = {
                **event,
                "provenance_status": "artifacts_prepared",
                "finalization": None,
            }
        elif event.get("event_type") == FINALIZE_ACTION and capture_id in current:
            current[capture_id] = {
                **current[capture_id],
                "provenance_status": "complete",
                "finalization": event,
            }
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_synthetic_capture(synthetic_capture_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_synthetic_captures()
            if item.get("synthetic_capture_id") == synthetic_capture_id
        ),
        None,
    )


def _candidate(batch: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in batch.get("candidates") or []
            if item.get("candidate_id") == candidate_id
        ),
        None,
    )


def _normalize_headers(value: Any) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(value, dict):
        return None, "response_headers_object_required"
    normalized = {}
    for key, raw_value in value.items():
        header = _required(key).lower()
        if not header:
            return None, "response_header_invalid"
        if header in SENSITIVE_HEADERS:
            return None, "sensitive_response_header_prohibited"
        normalized[header] = _required(raw_value)
    return dict(sorted(normalized.items())), None


def _normalize_redirects(
    value: Any,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not isinstance(value, list):
        return None, "redirect_chain_list_required"
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None, "redirect_chain_invalid"
        from_url = _normalize_url(item.get("from_url"))
        to_url = _normalize_url(item.get("to_url"))
        try:
            status_code = int(item.get("status_code"))
        except (TypeError, ValueError):
            return None, "redirect_chain_invalid"
        if from_url is None or to_url is None or status_code < 300 or status_code > 399:
            return None, "redirect_chain_invalid"
        normalized.append(
            {
                "from_url": from_url,
                "to_url": to_url,
                "status_code": status_code,
            }
        )
    return normalized, None


def _normalize_capture_files(
    value: Any,
) -> tuple[list[dict[str, Any]] | None, dict[str, bytes] | None, str | None]:
    if not isinstance(value, list) or not value:
        return None, None, "synthetic_capture_files_required"
    files = []
    payloads: dict[str, bytes] = {}
    roles = set()
    for item in value:
        if not isinstance(item, dict):
            return None, None, "synthetic_capture_file_invalid"
        role = _required(item.get("role"))
        filename = _required(item.get("filename"))
        media_type = _required(item.get("media_type")).lower()
        content = _content_bytes(item.get("content"))
        if role not in ROLE_MEDIA_TYPES or role in roles:
            return None, None, "synthetic_capture_role_invalid"
        if (
            not filename
            or PurePath(filename).name != filename
            or not _SAFE_FILENAME.fullmatch(filename)
        ):
            return None, None, "synthetic_capture_filename_invalid"
        if media_type not in ROLE_MEDIA_TYPES[role]:
            return None, None, "synthetic_capture_media_type_invalid"
        if content is None or not content:
            return None, None, "synthetic_capture_content_required"
        digest = hashlib.sha256(content).hexdigest()
        files.append(
            {
                "role": role,
                "filename": filename,
                "media_type": media_type,
                "byte_size": len(content),
                "content_sha256": digest,
            }
        )
        payloads[role] = content
        roles.add(role)
    if set(REQUIRED_ROLES) != roles:
        return None, None, "synthetic_capture_roles_incomplete"
    return sorted(files, key=lambda item: item["role"]), payloads, None


def prepare_synthetic_capture(
    *,
    actor: str,
    passive_discovery_batch_id: str,
    candidate_id: str,
    candidate_review_decision: str,
    candidate_review_reason: str,
    requested_url: str,
    final_url: str,
    redirect_chain: list[dict[str, Any]] | None,
    response_status: int,
    response_headers: dict[str, Any] | None,
    captured_at: str,
    adapter_name: str,
    adapter_version: str,
    capture_files: list[dict[str, Any]] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    passive_discovery_batch_id = _required(passive_discovery_batch_id)
    candidate_id = _required(candidate_id)
    candidate_review_decision = _required(candidate_review_decision)
    candidate_review_reason = _required(candidate_review_reason)
    requested_url_normalized = _normalize_url(requested_url)
    final_url_normalized = _normalize_url(final_url)
    captured_at_normalized = _time(captured_at)
    adapter_name = _required(adapter_name)
    adapter_version = _required(adapter_version)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_synthetic_capture_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not passive_discovery_batch_id or not candidate_id:
        return blocked("passive_candidate_binding_required")
    if candidate_review_decision != "approved_for_synthetic_capture":
        return blocked("explicit_candidate_capture_approval_required")
    if not candidate_review_reason:
        return blocked("candidate_review_reason_required")
    if requested_url_normalized is None or final_url_normalized is None:
        return blocked("capture_url_invalid")
    redirects, redirects_error = _normalize_redirects(redirect_chain)
    if redirects_error:
        return blocked(redirects_error)
    assert redirects is not None
    try:
        response_status = int(response_status)
    except (TypeError, ValueError):
        return blocked("response_status_invalid")
    if response_status < 100 or response_status > 599:
        return blocked("response_status_invalid")
    headers, headers_error = _normalize_headers(response_headers)
    if headers_error:
        return blocked(headers_error)
    assert headers is not None
    if captured_at_normalized is None:
        return blocked("captured_at_invalid")
    if not adapter_name or not adapter_version:
        return blocked("adapter_identity_required")
    files, payloads, files_error = _normalize_capture_files(capture_files)
    if files_error:
        return blocked(files_error)
    assert files is not None and payloads is not None
    if not reason:
        return blocked("administrative_reason_required")

    batch = find_passive_batch(passive_discovery_batch_id)
    if batch is None:
        return blocked("passive_discovery_batch_required")
    candidate = _candidate(batch, candidate_id)
    if candidate is None:
        return blocked("passive_archive_candidate_required")
    if candidate.get("record_status") != "accepted":
        return blocked("accepted_passive_archive_candidate_required")
    if candidate.get("review_required") is not True:
        return blocked("candidate_review_state_required")
    if candidate.get("candidate_url") != requested_url_normalized:
        return blocked("candidate_requested_url_mismatch")

    gate = find_gate_decision(str(batch.get("gate_decision_id") or ""))
    if gate is None or gate.get("decision") != "allow":
        return blocked("allowing_public_discovery_gate_required")
    if gate.get("live_network_eligible") is not False:
        return blocked("pre_live_network_gate_state_required")
    request = find_discovery_request(str(gate.get("discovery_request_id") or ""))
    if request is None:
        return blocked("public_discovery_request_required")
    request_manifest = request.get("manifest") or {}
    collection_binding = request_manifest.get("collection_job_binding") or {}
    collection_job_id = _required(collection_binding.get("collection_job_id"))
    attempt_number = int(collection_binding.get("attempt_number") or 1)
    case_id = _required(request_manifest.get("case_id"))
    purpose = _required(request_manifest.get("purpose"))
    if not collection_job_id or not case_id or not purpose:
        return blocked("synthetic_capture_authority_binding_incomplete")

    candidate_binding = {
        "passive_discovery_batch_id": passive_discovery_batch_id,
        "passive_discovery_event_sha256": batch.get(
            "passive_discovery_event_sha256"
        ),
        "candidate_id": candidate_id,
        "candidate_sha256": candidate.get("candidate_sha256"),
        "candidate_url": candidate.get("candidate_url"),
        "record_status": candidate.get("record_status"),
        "candidate_review_decision": candidate_review_decision,
        "candidate_review_reason": candidate_review_reason,
    }
    capture_manifest = {
        "synthetic_fixture": True,
        "case_id": case_id,
        "purpose": purpose,
        "collection_job_id": collection_job_id,
        "attempt_number": attempt_number,
        "gate_decision_id": gate.get("gate_decision_id"),
        "gate_decision_event_sha256": gate.get("gate_decision_event_sha256"),
        "candidate_binding": candidate_binding,
        "candidate_binding_sha256": _sha(candidate_binding),
        "requested_url": requested_url_normalized,
        "final_url": final_url_normalized,
        "redirect_chain": redirects,
        "response_status": response_status,
        "response_headers": headers,
        "captured_at": captured_at_normalized,
        "adapter": {"name": adapter_name, "version": adapter_version},
        "files": files,
    }
    capture_identity = {
        "candidate_binding_sha256": capture_manifest["candidate_binding_sha256"],
        "capture_manifest_sha256": _sha(capture_manifest),
    }
    synthetic_capture_id = f"synthetic-capture-{_sha(capture_identity)[:24]}"
    existing = find_synthetic_capture(synthetic_capture_id)
    if existing is not None:
        return {
            **existing,
            "status": "synthetic_capture_reused",
            "idempotent_replay": True,
            "next_action": (
                "review_completed_synthetic_provenance"
                if existing.get("provenance_status") == "complete"
                else "accept_synthetic_capture_artifacts_through_v29"
            ),
        }

    artifact_registrations = []
    for file_record in files:
        role = file_record["role"]
        artifact_result = register_artifact(
            actor=actor,
            collection_job_id=collection_job_id,
            attempt_number=attempt_number,
            source_reference=final_url_normalized,
            acquired_at=captured_at_normalized,
            content_sha256=file_record["content_sha256"],
            content_type=file_record["media_type"],
            byte_size=file_record["byte_size"],
            acquisition_method=f"synthetic_offline_{role}",
            provenance_metadata={
                "synthetic_fixture": True,
                "synthetic_capture_id": synthetic_capture_id,
                "capture_manifest_sha256": _sha(capture_manifest),
                "file_role": role,
                "filename": file_record["filename"],
                "raw_content_recorded_by_v38": False,
            },
            reason=f"{reason} Register synthetic {role} artifact.",
            confirmed=True,
            ip_address=ip_address,
        )
        if artifact_result.get("status") == "blocked":
            return blocked(
                "authoritative_artifact_registration_failed",
                role=role,
                authoritative_result=artifact_result,
            )
        artifact_registrations.append(
            {
                **file_record,
                "artifact_id": artifact_result.get("artifact_id"),
                "artifact_event_sha256": artifact_result.get(
                    "artifact_event_sha256"
                ),
                "initial_state": artifact_result.get("initial_state"),
                "duplicate_of_artifact_id": artifact_result.get(
                    "duplicate_of_artifact_id"
                ),
            }
        )

    content = {
        "event_type": PREPARE_ACTION,
        "synthetic_capture_id": synthetic_capture_id,
        "capture_manifest": capture_manifest,
        "capture_manifest_sha256": _sha(capture_manifest),
        "artifact_registrations": artifact_registrations,
        "artifact_registration_count": len(artifact_registrations),
        "all_artifacts_registered": all(
            item.get("artifact_id") for item in artifact_registrations
        ),
        "all_artifacts_initially_unquarantined": all(
            item.get("initial_state") == "registered"
            for item in artifact_registrations
        ),
        "reason": reason,
        "raw_content_recorded": False,
        "network_request_performed": False,
        "dns_lookup_performed": False,
        "archive_query_performed": False,
        "crawler_execution_performed": False,
        "browser_capture_performed": False,
        "source_registered": False,
        "import_registered": False,
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
        "synthetic_capture_event_id": f"synthetic-capture-event-{digest[:24]}",
        "synthetic_capture_event_sha256": digest,
    }
    result = _record(PREPARE_ACTION, actor, synthetic_capture_id, event, ip_address)
    return {
        **result,
        "status": "synthetic_capture_artifacts_prepared",
        "idempotent_replay": False,
        "next_action": "accept_synthetic_capture_artifacts_through_v29",
    }


def finalize_synthetic_capture_provenance(
    *,
    actor: str,
    synthetic_capture_id: str,
    publisher_or_operator: str,
    jurisdiction: str,
    source_type: str,
    terms_and_collection_notes: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    synthetic_capture_id = _required(synthetic_capture_id)
    publisher_or_operator = _required(publisher_or_operator)
    jurisdiction = _required(jurisdiction)
    source_type = _required(source_type)
    terms_and_collection_notes = _required(terms_and_collection_notes)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_synthetic_provenance_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not synthetic_capture_id:
        return blocked("synthetic_capture_required")
    if not publisher_or_operator or not jurisdiction or not source_type:
        return blocked("source_registration_metadata_required")
    if not terms_and_collection_notes:
        return blocked("terms_and_collection_notes_required")
    if not reason:
        return blocked("administrative_reason_required")

    prepared = find_synthetic_capture(synthetic_capture_id)
    if prepared is None:
        return blocked("prepared_synthetic_capture_required")
    if prepared.get("provenance_status") == "complete":
        return {
            **prepared,
            "status": "synthetic_capture_provenance_reused",
            "idempotent_replay": True,
            "next_action": "review_pre_live_network_gate_evidence",
        }

    artifact_bindings = []
    primary_binding = None
    for registration in prepared.get("artifact_registrations") or []:
        artifact_id = _required(registration.get("artifact_id"))
        artifact = find_artifact(artifact_id)
        if artifact is None:
            return blocked(
                "synthetic_capture_artifact_required", artifact_id=artifact_id
            )
        if artifact.get("artifact_state") != "accepted":
            return blocked(
                "accepted_synthetic_capture_artifact_required",
                artifact_id=artifact_id,
                artifact_state=artifact.get("artifact_state"),
            )
        if artifact.get("content_sha256") != registration.get("content_sha256"):
            return blocked(
                "synthetic_capture_artifact_hash_mismatch",
                artifact_id=artifact_id,
            )
        latest = (artifact.get("state_history") or [artifact])[-1]
        binding = {
            "role": registration.get("role"),
            "filename": registration.get("filename"),
            "media_type": registration.get("media_type"),
            "byte_size": registration.get("byte_size"),
            "content_sha256": registration.get("content_sha256"),
            "artifact_id": artifact_id,
            "artifact_state": artifact.get("artifact_state"),
            "artifact_event_sha256": latest.get("artifact_event_sha256"),
            "acquisition_sha256": artifact.get("acquisition_sha256"),
        }
        artifact_bindings.append(binding)
        if binding["role"] == "primary_html":
            primary_binding = binding
    if len(artifact_bindings) != len(REQUIRED_ROLES) or primary_binding is None:
        return blocked("complete_synthetic_artifact_set_required")

    manifest = prepared.get("capture_manifest") or {}
    adapter = manifest.get("adapter") or {}
    source_result = register_source(
        actor=actor,
        case_id=_required(manifest.get("case_id")),
        source_type=source_type,
        publisher_or_operator=publisher_or_operator,
        canonical_url=_required(manifest.get("requested_url")),
        retrieved_url=_required(manifest.get("final_url")),
        published_at=None,
        captured_at=_required(manifest.get("captured_at")),
        jurisdiction=jurisdiction,
        access_method="file_import",
        authentication_required=False,
        authorization_reference=None,
        original_or_derived="derived",
        terms_and_collection_notes=terms_and_collection_notes,
        content_sha256=_required(primary_binding.get("content_sha256")),
        capture_artifact_id=_required(primary_binding.get("artifact_id")),
        adapter_name=_required(adapter.get("name")),
        adapter_version=_required(adapter.get("version")),
        reason=f"{reason} Register the synthetic capture source.",
        confirmed=True,
        ip_address=ip_address,
    )
    if source_result.get("status") == "blocked":
        return blocked(
            "authoritative_source_registration_failed",
            authoritative_result=source_result,
        )

    source_id = _required(source_result.get("source_id"))
    import_result = register_import_envelope(
        actor=actor,
        case_id=_required(manifest.get("case_id")),
        purpose=_required(manifest.get("purpose")),
        artifact_id=_required(primary_binding.get("artifact_id")),
        content_sha256=_required(primary_binding.get("content_sha256")),
        original_filename=_required(primary_binding.get("filename")),
        media_type=_required(primary_binding.get("media_type")),
        export_format="html",
        tool_name="SyntheticCapturePilot",
        tool_version=VERSION,
        adapter_name=_required(adapter.get("name")),
        adapter_version=_required(adapter.get("version")),
        exported_at=_required(manifest.get("captured_at")),
        imported_at=_required(manifest.get("captured_at")),
        declared_record_count=1,
        source_references=[_required(manifest.get("final_url"))],
        collection_context={
            "synthetic_fixture": True,
            "synthetic_capture_id": synthetic_capture_id,
            "source_id": source_id,
            "artifact_bindings": artifact_bindings,
            "network_request_performed": False,
            "automatic_observation_promotion": False,
        },
        reason=f"{reason} Register explicit v37 handoff envelope.",
        confirmed=True,
        ip_address=ip_address,
    )
    if import_result.get("status") == "blocked":
        return blocked(
            "authoritative_import_registration_failed",
            authoritative_result=import_result,
        )

    final_binding = {
        "synthetic_capture_id": synthetic_capture_id,
        "synthetic_capture_event_sha256": prepared.get(
            "synthetic_capture_event_sha256"
        ),
        "capture_manifest_sha256": prepared.get("capture_manifest_sha256"),
        "artifact_bindings": sorted(
            artifact_bindings, key=lambda item: str(item.get("role") or "")
        ),
        "source_id": source_id,
        "source_event_sha256": source_result.get("source_event_sha256"),
        "operational_import_id": import_result.get("operational_import_id"),
        "operational_import_event_sha256": import_result.get(
            "operational_import_event_sha256"
        ),
    }
    content = {
        "event_type": FINALIZE_ACTION,
        "synthetic_capture_id": synthetic_capture_id,
        "final_binding": final_binding,
        "final_binding_sha256": _sha(final_binding),
        "pre_live_network_gate_satisfied": True,
        "required_proofs": {
            "synthetic_capture_envelope": True,
            "deterministic_content_sha256": True,
            "provenance_manifest": True,
            "accepted_v29_artifact_binding": True,
            "registered_v36_source_binding": True,
            "explicit_v37_import_handoff": True,
            "duplicate_and_quarantine_non_inflation": True,
        },
        "reason": reason,
        "raw_content_recorded": False,
        "network_request_performed": False,
        "dns_lookup_performed": False,
        "archive_query_performed": False,
        "crawler_execution_performed": False,
        "browser_capture_performed": False,
        "source_registered": True,
        "import_registered": True,
        "observation_created": False,
        "automatic_observation_promotion": False,
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
        "synthetic_provenance_event_id": f"synthetic-provenance-event-{digest[:24]}",
        "synthetic_provenance_event_sha256": digest,
    }
    result = _record(FINALIZE_ACTION, actor, synthetic_capture_id, event, ip_address)
    return {
        **result,
        "status": "synthetic_capture_provenance_finalized",
        "idempotent_replay": False,
        "next_action": "review_pre_live_network_gate_evidence",
    }
