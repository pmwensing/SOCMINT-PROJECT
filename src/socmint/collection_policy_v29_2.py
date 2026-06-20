from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import database
from .collection_job_contract_v29_1 import find_contract
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.collection_authorization_scope_policy.v29_2"
VERSION = "v29.2.0"
ACTIONS = (
    "collection_policy_created",
    "collection_policy_revised",
    "collection_policy_evaluated",
)
DECISIONS = ("allow", "deny")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "collection_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def history() -> list[dict[str, Any]]:
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
                "target_value": row.target_value,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _record(
    action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None
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
            "target_value": target,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def current_policies() -> list[dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    for event in history():
        if event.get("event_type") not in {
            "collection_policy_created",
            "collection_policy_revised",
        }:
            continue
        policy_id = str(event.get("policy_id") or "")
        if not policy_id:
            continue
        previous = str(event.get("supersedes_policy_id") or "")
        if previous in policies:
            policies[previous] = {
                **policies[previous],
                "policy_status": "superseded",
                "superseded_by_policy_id": policy_id,
            }
        policies[policy_id] = {**event, "policy_status": "active"}
    return sorted(
        policies.values(),
        key=lambda item: str((item.get("definition") or {}).get("name") or ""),
    )


def find_policy(policy_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in current_policies() if item.get("policy_id") == policy_id),
        None,
    )


def create_collection_policy(
    *,
    actor: str,
    name: str,
    description: str,
    permitted_source_classes: Any,
    permitted_purposes: Any,
    jurisdictions: Any,
    case_ids: Any,
    entity_ids: Any,
    source_ids: Any,
    deny_rules: Any,
    exclusions: Any,
    valid_from: str,
    expires_at: str,
    review_at: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    name = str(name or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_collection_policy_creation_confirmation_required")
    if not name:
        return blocked("collection_policy_name_required")
    if not reason:
        return blocked("administrative_reason_required")
    if name.lower() in {
        str((item.get("definition") or {}).get("name") or "").lower()
        for item in current_policies()
        if item.get("policy_status") == "active"
    }:
        return blocked("active_collection_policy_name_must_be_unique")
    definition = {
        "name": name,
        "description": str(description or "").strip(),
        "permitted_source_classes": sorted(
            {
                str(item).strip()
                for item in (permitted_source_classes or [])
                if str(item).strip()
            }
        ),
        "permitted_purposes": sorted(
            {
                str(item).strip()
                for item in (permitted_purposes or [])
                if str(item).strip()
            }
        ),
        "jurisdictions": sorted(
            {str(item).strip() for item in (jurisdictions or []) if str(item).strip()}
        ),
        "case_ids": sorted(
            {str(item).strip() for item in (case_ids or []) if str(item).strip()}
        ),
        "entity_ids": sorted(
            {str(item).strip() for item in (entity_ids or []) if str(item).strip()}
        ),
        "source_ids": sorted(
            {str(item).strip() for item in (source_ids or []) if str(item).strip()}
        ),
        "deny_rules": deny_rules if isinstance(deny_rules, list) else [],
        "exclusions": exclusions if isinstance(exclusions, list) else [],
        "valid_from": str(valid_from or "").strip() or None,
        "expires_at": str(expires_at or "").strip() or None,
        "review_at": str(review_at or "").strip() or None,
    }
    content = {
        "event_type": "collection_policy_created",
        "definition": definition,
        "definition_sha256": _sha(definition),
        "reason": reason,
        "revision": 1,
        "supersedes_policy_id": None,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "policy_id": f"collection-policy-{digest[:24]}",
        "policy_event_id": f"collection-policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "collection_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(ACTIONS[0], actor, name, event, ip_address),
        "status": "collection_policy_created",
        "next_action": "evaluate_collection_job_policy",
    }


def revise_collection_policy(
    policy_id: str,
    *,
    actor: str,
    definition: Any,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    previous = find_policy(policy_id)
    if previous is None or previous.get("policy_status") != "active":
        return blocked("active_collection_policy_required")
    if confirmed is not True:
        return blocked("explicit_collection_policy_revision_confirmation_required")
    if not str(reason or "").strip():
        return blocked("administrative_reason_required")
    revised = definition if isinstance(definition, dict) else {}
    if not str(revised.get("name") or "").strip():
        return blocked("collection_policy_name_required")
    binding = {
        "policy_id": policy_id,
        "policy_event_id": previous.get("policy_event_id"),
        "policy_event_sha256": previous.get("policy_event_sha256"),
        "definition_sha256": previous.get("definition_sha256"),
        "revision": previous.get("revision"),
    }
    content = {
        "event_type": "collection_policy_revised",
        "definition": revised,
        "definition_sha256": _sha(revised),
        "reason": str(reason).strip(),
        "revision": int(previous.get("revision") or 1) + 1,
        "supersedes_policy_id": policy_id,
        "previous_policy_binding": binding,
        "previous_policy_binding_sha256": _sha(binding),
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "policy_id": f"collection-policy-{digest[:24]}",
        "policy_event_id": f"collection-policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "prior_policy_event_mutated": False,
        "collection_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    return {
        **_record(ACTIONS[1], actor, str(revised.get("name")), event, ip_address),
        "status": "collection_policy_revised",
        "next_action": "reevaluate_collection_job_policy",
    }


def _rule_matches(rule: Any, contract: dict[str, Any]) -> bool:
    if not isinstance(rule, dict):
        return False
    field = str(rule.get("field") or "").strip()
    value = rule.get("value")
    actual = contract.get(field)
    if isinstance(value, list):
        return actual in value
    return actual == value


def evaluate_collection_job_policy(
    *,
    actor: str,
    collection_job_id: str,
    jurisdiction: str,
    reason: str,
    confirmed: bool,
    ip_address: str | None = None,
) -> dict[str, Any]:
    contract = find_contract(collection_job_id)
    if contract is None:
        return blocked("collection_job_contract_required")
    if confirmed is not True:
        return blocked("explicit_collection_policy_evaluation_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("evaluation_reason_required")
    now = datetime.now(timezone.utc)
    active = []
    denied_by = []
    allowed_by = []
    explanations = []
    for policy in current_policies():
        if policy.get("policy_status") != "active":
            continue
        definition = policy.get("definition") or {}
        valid_from = _parse_time(definition.get("valid_from"))
        expires_at = _parse_time(definition.get("expires_at"))
        if valid_from and now < valid_from:
            continue
        if expires_at and now >= expires_at:
            continue
        active.append(policy)
        policy_id = str(policy.get("policy_id"))
        source_classes = set(definition.get("permitted_source_classes") or [])
        purposes = set(definition.get("permitted_purposes") or [])
        jurisdictions = set(definition.get("jurisdictions") or [])
        case_ids = set(definition.get("case_ids") or [])
        entity_ids = set(definition.get("entity_ids") or [])
        source_ids = set(definition.get("source_ids") or [])
        matches_allow = True
        if source_classes and contract.get("connector") not in source_classes:
            matches_allow = False
        if purposes and contract.get("purpose") not in purposes:
            matches_allow = False
        if jurisdictions and jurisdiction not in jurisdictions:
            matches_allow = False
        if case_ids and contract.get("case_id") not in case_ids:
            matches_allow = False
        if entity_ids and contract.get("entity_id") not in entity_ids:
            matches_allow = False
        if source_ids and contract.get("source_id") not in source_ids:
            matches_allow = False
        deny_match = any(
            _rule_matches(rule, contract) for rule in definition.get("deny_rules") or []
        )
        exclusion_match = any(
            _rule_matches(rule, contract) for rule in definition.get("exclusions") or []
        )
        if deny_match or exclusion_match:
            denied_by.append(policy_id)
            explanations.append(
                {
                    "policy_id": policy_id,
                    "result": "deny",
                    "deny_match": deny_match,
                    "exclusion_match": exclusion_match,
                }
            )
        elif matches_allow:
            allowed_by.append(policy_id)
            explanations.append({"policy_id": policy_id, "result": "allow"})
        else:
            explanations.append({"policy_id": policy_id, "result": "not_applicable"})
    decision = "deny" if denied_by or not allowed_by else "allow"
    binding = {
        "collection_job_id": collection_job_id,
        "contract_event_sha256": contract.get("collection_job_event_sha256"),
        "idempotency_key": contract.get("idempotency_key"),
        "attempt_number": contract.get("attempt_number"),
    }
    evaluation = {
        "decision": decision,
        "allowed_by_policy_ids": sorted(allowed_by),
        "denied_by_policy_ids": sorted(denied_by),
        "jurisdiction": str(jurisdiction or "").strip(),
        "explanations": explanations,
        "active_policy_count": len(active),
    }
    content = {
        "event_type": "collection_policy_evaluated",
        "collection_job_id": collection_job_id,
        "contract_binding": binding,
        "contract_binding_sha256": _sha(binding),
        "evaluation": evaluation,
        "evaluation_sha256": _sha(evaluation),
        "reason": reason,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "policy_evaluation_id": f"collection-policy-evaluation-{digest[:24]}",
        "policy_event_id": f"collection-policy-event-{digest[:24]}",
        "policy_event_sha256": digest,
        "deny_overrides_allow": True,
        "collection_job_mutated": False,
        "connector_execution_performed": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[2], actor, collection_job_id, event, ip_address)
    return {
        **result,
        "status": "collection_policy_evaluated",
        "next_action": "authorize_collection_job"
        if decision == "allow"
        else "resolve_collection_policy_denial",
    }
