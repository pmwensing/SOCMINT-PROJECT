from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .collection_policy_v29_2 import (
    DECISIONS,
    SCHEMA,
    VERSION,
    current_policies,
    history,
)


def _parse_time(value: Any):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_collection_policy_workspace(
    *, review_due_within_days: int = 30
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    review_cutoff = now + timedelta(days=max(1, int(review_due_within_days)))
    policies = current_policies()
    events = history()
    active = [item for item in policies if item.get("policy_status") == "active"]
    evaluations = [
        item
        for item in events
        if item.get("event_type") == "collection_policy_evaluated"
    ]
    expired = []
    review_due = []
    findings = []
    for policy in active:
        definition = policy.get("definition") or {}
        expires_at = _parse_time(definition.get("expires_at"))
        review_at = _parse_time(definition.get("review_at"))
        if expires_at and expires_at <= now:
            expired.append(
                {
                    "policy_id": policy.get("policy_id"),
                    "name": definition.get("name"),
                    "expires_at": expires_at.isoformat(),
                }
            )
            findings.append(
                {
                    "severity": "high",
                    "key": "collection_policy_expired",
                    "policy_id": policy.get("policy_id"),
                }
            )
        if review_at and review_at <= review_cutoff:
            review_due.append(
                {
                    "policy_id": policy.get("policy_id"),
                    "name": definition.get("name"),
                    "review_at": review_at.isoformat(),
                }
            )
        if not definition.get("permitted_source_classes"):
            findings.append(
                {
                    "severity": "medium",
                    "key": "policy_without_source_class",
                    "policy_id": policy.get("policy_id"),
                }
            )
        if not definition.get("permitted_purposes"):
            findings.append(
                {
                    "severity": "medium",
                    "key": "policy_without_purpose",
                    "policy_id": policy.get("policy_id"),
                }
            )
        if not definition.get("jurisdictions"):
            findings.append(
                {
                    "severity": "low",
                    "key": "policy_without_jurisdiction",
                    "policy_id": policy.get("policy_id"),
                }
            )
        if not any(
            (
                definition.get("case_ids"),
                definition.get("entity_ids"),
                definition.get("source_ids"),
            )
        ):
            findings.append(
                {
                    "severity": "medium",
                    "key": "policy_without_scope_binding",
                    "policy_id": policy.get("policy_id"),
                }
            )
    decision_counts = Counter(
        str((item.get("evaluation") or {}).get("decision") or "unknown")
        for item in evaluations
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "policies": policies,
        "active_policies": active,
        "policy_count": len(policies),
        "active_policy_count": len(active),
        "expired_policies": expired,
        "expired_policy_count": len(expired),
        "review_due_policies": review_due,
        "review_due_policy_count": len(review_due),
        "evaluations": evaluations[-250:],
        "evaluation_count": len(evaluations),
        "evaluation_decision_counts": dict(sorted(decision_counts.items())),
        "decision_options": list(DECISIONS),
        "policy_findings": findings,
        "policy_finding_count": len(findings),
        "collection_policy_history": events[-300:],
        "collection_policy_event_count": len(events),
        "deny_overrides_allow": True,
        "evaluation_mutates_collection_job": False,
        "connector_execution_available": False,
        "case_access_scope_changed": False,
        "secret_values_visible": False,
        "next_action": "review_collection_authorization_and_scope",
    }
