from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import database
from .collection_job_contract_v29_1 import TERMINAL_STATES, find_contract
from .collection_policy_v29_2 import history as policy_history
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.public_discovery_request.v38_1"
VERSION = "v38.1.0"
REGISTER_ACTION = "public_discovery_request_registered"
ADAPTER_INTENTS = (
    "common_crawl_index",
    "internet_archive_index",
    "synthetic_capture",
    "public_http",
    "browsertrix",
)
REQUIRED_LIMIT_KEYS = (
    "allowed_domains",
    "max_pages",
    "max_depth",
    "delay_seconds",
    "concurrent_requests_per_domain",
    "max_redirects",
    "max_response_bytes",
    "allowed_content_types",
)


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_required(item) for item in value if _required(item)})


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
    discovery_request_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=REGISTER_ACTION,
            target_value=discovery_request_id,
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


def current_discovery_requests() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        request_id = str(event.get("discovery_request_id") or "")
        if request_id:
            current[request_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_discovery_request(discovery_request_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_discovery_requests()
            if item.get("discovery_request_id") == discovery_request_id
        ),
        None,
    )


def _find_by_idempotency_key(idempotency_key: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_discovery_requests()
            if item.get("idempotency_key") == idempotency_key
        ),
        None,
    )


def _allowing_policy_evaluation(
    collection_job_id: str,
    policy_evaluation_id: str,
    contract: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    evaluation = next(
        (
            item
            for item in reversed(policy_history())
            if item.get("event_type") == "collection_policy_evaluated"
            and item.get("policy_evaluation_id") == policy_evaluation_id
        ),
        None,
    )
    if evaluation is None:
        return None, "collection_policy_evaluation_required"
    if evaluation.get("collection_job_id") != collection_job_id:
        return None, "policy_evaluation_collection_job_mismatch"
    if (evaluation.get("evaluation") or {}).get("decision") != "allow":
        return None, "allowing_collection_policy_evaluation_required"
    binding = evaluation.get("contract_binding") or {}
    if binding.get("collection_job_id") != collection_job_id:
        return None, "policy_evaluation_contract_binding_mismatch"
    if binding.get("contract_event_sha256") != contract.get(
        "collection_job_event_sha256"
    ):
        return None, "policy_evaluation_contract_binding_mismatch"
    return (
        {
            "policy_evaluation_id": evaluation.get("policy_evaluation_id"),
            "policy_event_sha256": evaluation.get("policy_event_sha256"),
            "evaluation_sha256": evaluation.get("evaluation_sha256"),
            "decision": "allow",
            "allowed_by_policy_ids": sorted(
                (evaluation.get("evaluation") or {}).get(
                    "allowed_by_policy_ids"
                )
                or []
            ),
            "jurisdiction": (evaluation.get("evaluation") or {}).get(
                "jurisdiction"
            ),
        },
        None,
    )


def _normalize_limits(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict):
        return None, "resource_limits_object_required"
    if any(key not in value for key in REQUIRED_LIMIT_KEYS):
        return None, "resource_limits_incomplete"

    allowed_domains = _string_list(value.get("allowed_domains"))
    content_types = _string_list(value.get("allowed_content_types"))
    if not allowed_domains or not content_types:
        return None, "resource_limits_incomplete"
    if any(
        "/" in domain
        or "://" in domain
        or "@" in domain
        or not domain.strip(".")
        for domain in allowed_domains
    ):
        return None, "allowed_domain_invalid"

    integer_keys = (
        "max_pages",
        "max_depth",
        "concurrent_requests_per_domain",
        "max_redirects",
        "max_response_bytes",
    )
    numeric: dict[str, int | float] = {}
    for key in integer_keys:
        value_item = value.get(key)
        if isinstance(value_item, bool):
            return None, "resource_limit_invalid"
        try:
            parsed = int(value_item)
        except (TypeError, ValueError):
            return None, "resource_limit_invalid"
        if parsed < 0:
            return None, "resource_limit_invalid"
        numeric[key] = parsed
    try:
        delay_seconds = float(value.get("delay_seconds"))
    except (TypeError, ValueError):
        return None, "resource_limit_invalid"
    if delay_seconds < 0:
        return None, "resource_limit_invalid"

    return (
        {
            "allowed_domains": sorted(domain.lower() for domain in allowed_domains),
            "max_pages": numeric["max_pages"],
            "max_depth": numeric["max_depth"],
            "delay_seconds": delay_seconds,
            "concurrent_requests_per_domain": numeric[
                "concurrent_requests_per_domain"
            ],
            "max_redirects": numeric["max_redirects"],
            "max_response_bytes": numeric["max_response_bytes"],
            "allowed_content_types": content_types,
        },
        None,
    )


def register_discovery_request(
    *,
    actor: str,
    case_id: str,
    purpose: str,
    collection_job_id: str,
    policy_evaluation_id: str,
    source_class: str,
    adapter_intent: str,
    jurisdiction: str,
    query_terms: list[str] | None,
    seed_urls: list[str] | None,
    resource_limits: dict[str, Any] | None,
    idempotency_key: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    case_id = _required(case_id)
    purpose = _required(purpose)
    collection_job_id = _required(collection_job_id)
    policy_evaluation_id = _required(policy_evaluation_id)
    source_class = _required(source_class)
    adapter_intent = _required(adapter_intent)
    jurisdiction = _required(jurisdiction)
    query_terms = _string_list(query_terms)
    raw_seed_urls = _string_list(seed_urls)
    idempotency_key = _required(idempotency_key)
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_discovery_request_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not case_id or not purpose:
        return blocked("case_and_purpose_required")
    if not collection_job_id:
        return blocked("collection_job_binding_required")
    if not policy_evaluation_id:
        return blocked("policy_evaluation_binding_required")
    if not source_class:
        return blocked("source_class_required")
    if adapter_intent not in ADAPTER_INTENTS:
        return blocked("adapter_intent_invalid")
    if not jurisdiction:
        return blocked("jurisdiction_required")
    if not query_terms and not raw_seed_urls:
        return blocked("query_or_seed_required")
    if not idempotency_key:
        return blocked("idempotency_key_required")
    if not reason:
        return blocked("administrative_reason_required")

    seed_urls = []
    for raw_url in raw_seed_urls:
        normalized = _normalize_url(raw_url)
        if normalized is None:
            return blocked("seed_url_invalid")
        seed_urls.append(normalized)
    seed_urls = sorted(set(seed_urls))

    normalized_limits, limits_error = _normalize_limits(resource_limits)
    if limits_error:
        return blocked(limits_error)
    assert normalized_limits is not None

    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    if contract.get("current_state") in TERMINAL_STATES:
        return blocked("active_collection_job_required")
    if contract.get("case_id") != case_id:
        return blocked("discovery_case_collection_job_mismatch")
    if contract.get("purpose") != purpose:
        return blocked("discovery_purpose_collection_job_mismatch")
    if contract.get("connector") != source_class:
        return blocked("discovery_source_class_collection_job_mismatch")

    evaluation_binding, evaluation_error = _allowing_policy_evaluation(
        collection_job_id,
        policy_evaluation_id,
        contract,
    )
    if evaluation_error:
        return blocked(evaluation_error)
    assert evaluation_binding is not None
    if evaluation_binding.get("jurisdiction") != jurisdiction:
        return blocked("discovery_jurisdiction_policy_mismatch")

    contract_binding = {
        "collection_job_id": collection_job_id,
        "collection_job_event_sha256": contract.get("collection_job_event_sha256"),
        "definition_sha256": contract.get("definition_sha256"),
        "current_state": contract.get("current_state"),
        "attempt_number": contract.get("attempt_number"),
        "case_id": contract.get("case_id"),
        "entity_id": contract.get("entity_id"),
        "source_id": contract.get("source_id"),
    }
    manifest = {
        "case_id": case_id,
        "purpose": purpose,
        "collection_job_binding": contract_binding,
        "collection_job_binding_sha256": _sha(contract_binding),
        "policy_evaluation_binding": evaluation_binding,
        "policy_evaluation_binding_sha256": _sha(evaluation_binding),
        "source_class": source_class,
        "adapter_intent": adapter_intent,
        "jurisdiction": jurisdiction,
        "query_terms": query_terms,
        "seed_urls": seed_urls,
        "resource_limits": normalized_limits,
    }
    definition_sha256 = _sha(manifest)
    existing = _find_by_idempotency_key(idempotency_key)
    if existing is not None:
        if existing.get("definition_sha256") != definition_sha256:
            return blocked("idempotency_key_conflict")
        return {
            **existing,
            "status": "public_discovery_request_reused",
            "idempotent_replay": True,
            "next_action": "evaluate_public_discovery_policy_gate",
        }

    identity = {
        "case_id": case_id,
        "collection_job_id": collection_job_id,
        "policy_evaluation_id": policy_evaluation_id,
        "idempotency_key": idempotency_key,
        "definition_sha256": definition_sha256,
    }
    request_id = f"public-discovery-request-{_sha(identity)[:24]}"
    content = {
        "event_type": REGISTER_ACTION,
        "discovery_request_id": request_id,
        "idempotency_key": idempotency_key,
        "manifest": manifest,
        "manifest_sha256": definition_sha256,
        "definition_sha256": definition_sha256,
        "reason": reason,
        "execution_eligible": False,
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
        "discovery_request_event_id": f"public-discovery-event-{digest[:24]}",
        "discovery_request_event_sha256": digest,
    }
    result = _record(actor, request_id, event, ip_address)
    return {
        **result,
        "status": "public_discovery_request_registered",
        "idempotent_replay": False,
        "next_action": "evaluate_public_discovery_policy_gate",
    }
