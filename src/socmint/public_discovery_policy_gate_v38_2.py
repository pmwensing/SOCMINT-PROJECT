from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .public_discovery_request_v38_1 import find_discovery_request

SCHEMA = "socmint.public_discovery_policy_gate.v38_2"
VERSION = "v38.2.0"
EVALUATE_ACTION = "public_discovery_policy_gate_evaluated"
SOURCE_TIERS = (
    "tier_1_official",
    "tier_2_media_archive",
    "tier_3_public_document_discovery",
    "tier_4_review_before_use",
)
ROBOTS_DECISIONS = ("allow", "disallow", "unavailable")
TERMS_DECISIONS = ("reviewed_allow", "reviewed_block", "unknown")
ACCESS_INDICATOR_KEYS = (
    "login_required",
    "paywall_required",
    "captcha_required",
    "private_account",
)
PROHIBITED_QUERY_FRAGMENTS = (
    "credential dump",
    "password dump",
    "combo list",
    "leak database",
    "login bypass",
    "captcha bypass",
    "paywall bypass",
    "private account",
    "dark web",
    ".onion",
    " tor hidden service",
)
EXCLUDED_SCOPE_FRAGMENTS = (
    "71 cowdy",
    "81 cowdy",
    "cowdy street",
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


def _history() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=EVALUATE_ACTION)
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
    gate_decision_id: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=EVALUATE_ACTION,
            target_value=gate_decision_id,
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


def current_gate_decisions() -> list[dict[str, Any]]:
    current: dict[str, dict[str, Any]] = {}
    for event in _history():
        gate_id = str(event.get("gate_decision_id") or "")
        if gate_id:
            current[gate_id] = event
    return sorted(
        current.values(),
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )


def find_gate_decision(gate_decision_id: str) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in current_gate_decisions()
            if item.get("gate_decision_id") == gate_decision_id
        ),
        None,
    )


def _domain_allowed(host: str, allowed_domains: set[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def _normalize_policy_limits(
    value: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict):
        return None, "policy_limits_object_required"
    required = (
        "allowed_domains",
        "max_pages",
        "max_depth",
        "min_delay_seconds",
        "max_concurrent_requests_per_domain",
        "max_redirects",
        "max_response_bytes",
        "allowed_content_types",
    )
    if any(key not in value for key in required):
        return None, "policy_limits_incomplete"
    domains = sorted(domain.lower() for domain in _string_list(value.get("allowed_domains")))
    content_types = _string_list(value.get("allowed_content_types"))
    if not domains or not content_types:
        return None, "policy_limits_incomplete"
    if any(
        "/" in domain
        or "://" in domain
        or "@" in domain
        or not domain.strip(".")
        for domain in domains
    ):
        return None, "policy_allowed_domain_invalid"

    parsed: dict[str, int | float] = {}
    for key in (
        "max_pages",
        "max_depth",
        "max_concurrent_requests_per_domain",
        "max_redirects",
        "max_response_bytes",
    ):
        raw = value.get(key)
        if isinstance(raw, bool):
            return None, "policy_limit_invalid"
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return None, "policy_limit_invalid"
        if number < 0:
            return None, "policy_limit_invalid"
        parsed[key] = number
    try:
        min_delay_seconds = float(value.get("min_delay_seconds"))
    except (TypeError, ValueError):
        return None, "policy_limit_invalid"
    if min_delay_seconds < 0:
        return None, "policy_limit_invalid"

    return (
        {
            "allowed_domains": domains,
            "max_pages": parsed["max_pages"],
            "max_depth": parsed["max_depth"],
            "min_delay_seconds": min_delay_seconds,
            "max_concurrent_requests_per_domain": parsed[
                "max_concurrent_requests_per_domain"
            ],
            "max_redirects": parsed["max_redirects"],
            "max_response_bytes": parsed["max_response_bytes"],
            "allowed_content_types": content_types,
        },
        None,
    )


def _evaluate_limits(
    request_limits: dict[str, Any],
    policy_limits: dict[str, Any],
) -> list[str]:
    blockers = []
    request_domains = set(request_limits.get("allowed_domains") or [])
    policy_domains = set(policy_limits.get("allowed_domains") or [])
    if not request_domains.issubset(policy_domains):
        blockers.append("requested_domain_outside_policy_allowlist")
    if int(request_limits.get("max_pages") or 0) > int(policy_limits["max_pages"]):
        blockers.append("requested_page_limit_exceeds_policy")
    if int(request_limits.get("max_depth") or 0) > int(policy_limits["max_depth"]):
        blockers.append("requested_depth_limit_exceeds_policy")
    if float(request_limits.get("delay_seconds") or 0) < float(
        policy_limits["min_delay_seconds"]
    ):
        blockers.append("requested_delay_below_policy_minimum")
    if int(request_limits.get("concurrent_requests_per_domain") or 0) > int(
        policy_limits["max_concurrent_requests_per_domain"]
    ):
        blockers.append("requested_concurrency_exceeds_policy")
    if int(request_limits.get("max_redirects") or 0) > int(
        policy_limits["max_redirects"]
    ):
        blockers.append("requested_redirect_limit_exceeds_policy")
    if int(request_limits.get("max_response_bytes") or 0) > int(
        policy_limits["max_response_bytes"]
    ):
        blockers.append("requested_response_size_exceeds_policy")
    request_types = set(request_limits.get("allowed_content_types") or [])
    policy_types = set(policy_limits.get("allowed_content_types") or [])
    if not request_types.issubset(policy_types):
        blockers.append("requested_content_type_outside_policy")
    return blockers


def evaluate_discovery_request(
    *,
    actor: str,
    discovery_request_id: str,
    source_tier: str,
    allowlisted_domains: list[str] | None,
    direct_case_relevance: bool,
    candidate_entity_reviewed: bool,
    public_access_confirmed: bool,
    robots_decision: str,
    terms_decision: str,
    access_indicators: dict[str, Any] | None,
    policy_limits: dict[str, Any] | None,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    actor = _required(actor)
    discovery_request_id = _required(discovery_request_id)
    source_tier = _required(source_tier)
    robots_decision = _required(robots_decision)
    terms_decision = _required(terms_decision)
    allowlisted_domains = sorted(
        domain.lower() for domain in _string_list(allowlisted_domains)
    )
    reason = _required(reason)

    if confirmed is not True:
        return blocked("explicit_discovery_gate_confirmation_required")
    if not actor:
        return blocked("actor_required")
    if not discovery_request_id:
        return blocked("discovery_request_required")
    if source_tier not in SOURCE_TIERS:
        return blocked("source_tier_invalid")
    if robots_decision not in ROBOTS_DECISIONS:
        return blocked("robots_decision_invalid")
    if terms_decision not in TERMS_DECISIONS:
        return blocked("terms_decision_invalid")
    if not allowlisted_domains:
        return blocked("source_allowlist_required")
    if any(
        "/" in domain or "://" in domain or "@" in domain
        for domain in allowlisted_domains
    ):
        return blocked("source_allowlist_invalid")
    if not isinstance(direct_case_relevance, bool) or not isinstance(
        candidate_entity_reviewed, bool
    ):
        return blocked("relevance_flags_must_be_boolean")
    if not isinstance(public_access_confirmed, bool):
        return blocked("public_access_flag_must_be_boolean")
    indicators = access_indicators if isinstance(access_indicators, dict) else None
    if indicators is None or any(key not in indicators for key in ACCESS_INDICATOR_KEYS):
        return blocked("access_indicators_incomplete")
    if any(not isinstance(indicators.get(key), bool) for key in ACCESS_INDICATOR_KEYS):
        return blocked("access_indicators_must_be_boolean")
    normalized_policy_limits, limits_error = _normalize_policy_limits(policy_limits)
    if limits_error:
        return blocked(limits_error)
    assert normalized_policy_limits is not None
    if not reason:
        return blocked("evaluation_reason_required")

    request = find_discovery_request(discovery_request_id)
    if request is None:
        return blocked("public_discovery_request_required")
    manifest = request.get("manifest") or {}
    request_binding = {
        "discovery_request_id": discovery_request_id,
        "discovery_request_event_sha256": request.get(
            "discovery_request_event_sha256"
        ),
        "manifest_sha256": request.get("manifest_sha256"),
        "case_id": manifest.get("case_id"),
        "collection_job_id": (
            manifest.get("collection_job_binding") or {}
        ).get("collection_job_id"),
        "policy_evaluation_id": (
            manifest.get("policy_evaluation_binding") or {}
        ).get("policy_evaluation_id"),
    }

    decision_blockers: list[str] = []
    if not direct_case_relevance and not candidate_entity_reviewed:
        decision_blockers.append("direct_relevance_or_reviewed_candidate_required")
    if not public_access_confirmed:
        decision_blockers.append("public_access_required")
    if robots_decision != "allow":
        decision_blockers.append("robots_allow_required")
    if terms_decision != "reviewed_allow":
        decision_blockers.append("terms_review_allow_required")
    for key in ACCESS_INDICATOR_KEYS:
        if indicators.get(key) is True:
            decision_blockers.append(f"{key}_blocked")

    query_text = " ".join(manifest.get("query_terms") or []).lower()
    if any(fragment in query_text for fragment in EXCLUDED_SCOPE_FRAGMENTS):
        decision_blockers.append("excluded_address_query_blocked")
    if any(fragment in query_text for fragment in PROHIBITED_QUERY_FRAGMENTS):
        decision_blockers.append("prohibited_query_intent_blocked")

    allowed_domain_set = set(allowlisted_domains)
    request_domains = set((manifest.get("resource_limits") or {}).get("allowed_domains") or [])
    if not request_domains.issubset(allowed_domain_set):
        decision_blockers.append("request_domain_not_source_allowlisted")
    for seed_url in manifest.get("seed_urls") or []:
        host = (urlsplit(seed_url).hostname or "").lower()
        if not host or not _domain_allowed(host, allowed_domain_set):
            decision_blockers.append("seed_url_not_source_allowlisted")
            break

    decision_blockers.extend(
        _evaluate_limits(
            manifest.get("resource_limits") or {},
            normalized_policy_limits,
        )
    )
    decision_blockers = sorted(set(decision_blockers))
    decision = "allow" if not decision_blockers else "block"
    evaluation = {
        "source_tier": source_tier,
        "allowlisted_domains": allowlisted_domains,
        "direct_case_relevance": direct_case_relevance,
        "candidate_entity_reviewed": candidate_entity_reviewed,
        "public_access_confirmed": public_access_confirmed,
        "robots_decision": robots_decision,
        "terms_decision": terms_decision,
        "access_indicators": {key: indicators[key] for key in ACCESS_INDICATOR_KEYS},
        "policy_limits": normalized_policy_limits,
        "decision": decision,
        "decision_blockers": decision_blockers,
    }
    identity = {
        "request_binding": request_binding,
        "evaluation_sha256": _sha(evaluation),
    }
    gate_id = f"public-discovery-gate-{_sha(identity)[:24]}"
    existing = find_gate_decision(gate_id)
    if existing is not None:
        return {
            **existing,
            "status": "public_discovery_policy_gate_reused",
            "idempotent_replay": True,
            "next_action": (
                "stage_offline_passive_discovery"
                if existing.get("decision") == "allow"
                else "resolve_public_discovery_gate_blockers"
            ),
        }

    content = {
        "event_type": EVALUATE_ACTION,
        "gate_decision_id": gate_id,
        "discovery_request_id": discovery_request_id,
        "request_binding": request_binding,
        "request_binding_sha256": _sha(request_binding),
        "evaluation": evaluation,
        "evaluation_sha256": _sha(evaluation),
        "decision": decision,
        "decision_blockers": decision_blockers,
        "passive_discovery_eligible": decision == "allow",
        "live_network_eligible": False,
        "reason": reason,
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
        "gate_decision_event_id": f"public-discovery-gate-event-{digest[:24]}",
        "gate_decision_event_sha256": digest,
    }
    result = _record(actor, gate_id, event, ip_address)
    return {
        **result,
        "status": "public_discovery_policy_gate_evaluated",
        "idempotent_replay": False,
        "next_action": (
            "stage_offline_passive_discovery"
            if decision == "allow"
            else "resolve_public_discovery_gate_blockers"
        ),
    }
