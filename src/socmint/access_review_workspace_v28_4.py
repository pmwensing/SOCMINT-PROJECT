from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .access_policy_events_v28_2 import current_access_rules, current_roles
from .access_policy_workspace_v28_2 import resolve_role_permissions
from .access_review_events_v28_4 import DECISIONS, SCHEMA, VERSION, current_reviews, history


def _parse_time(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _expired_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    expired = []
    for rule in rules:
        if rule.get("rule_status") != "active":
            continue
        definition = rule.get("definition") or {}
        expires_at = _parse_time(definition.get("expires_at") or rule.get("expires_at"))
        if expires_at and expires_at < now:
            expired.append({
                "access_rule_id": rule.get("access_rule_id"),
                "subject_type": definition.get("subject_type"),
                "subject_id": definition.get("subject_id"),
                "case_id": definition.get("case_id"),
                "expires_at": expires_at.isoformat(),
                "finding": "expired_active_access_rule",
            })
    return expired


def _excessive_access_findings(roles: list[dict[str, Any]], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    for role in roles:
        if role.get("role_status") != "active":
            continue
        role_id = str(role.get("role_id") or "")
        definition = role.get("definition") or {}
        resolved = resolve_role_permissions(role_id)
        if resolved.get("effective_permission_count", 0) >= 12 and str(definition.get("name") or "").lower() != "admin":
            findings.append({"finding":"broad_non_admin_role","role_id":role_id,"role_name":definition.get("name"),"permission_count":resolved.get("effective_permission_count")})
    for rule in rules:
        if rule.get("rule_status") != "active":
            continue
        definition = rule.get("definition") or {}
        permissions = list(definition.get("permissions") or [])
        if definition.get("effect") == "allow" and len(permissions) >= 8:
            findings.append({"finding":"broad_case_access_rule","access_rule_id":rule.get("access_rule_id"),"subject_type":definition.get("subject_type"),"subject_id":definition.get("subject_id"),"case_id":definition.get("case_id"),"permission_count":len(permissions)})
    return findings


def build_access_review_workspace() -> dict[str, Any]:
    reviews = current_reviews()
    events = history()
    rules = current_access_rules()
    roles = current_roles()
    open_reviews = [item for item in reviews if item.get("review_status") == "open"]
    closed_reviews = [item for item in reviews if item.get("review_status") == "closed"]
    decisions = [decision for review in reviews for decision in review.get("decisions", [])]
    decision_counts = Counter(str((item.get("decision_record") or {}).get("decision") or "unknown") for item in decisions)
    pending_assignments = []
    remediation_queue = []
    for review in open_reviews:
        decided_ids = {str(item.get("review_assignment_id")) for item in review.get("decisions", [])}
        for assignment in review.get("assignments", []):
            if str(assignment.get("review_assignment_id")) not in decided_ids:
                pending_assignments.append({"review_id":review.get("review_id"),**assignment})
    for review in reviews:
        for decision in review.get("decisions", []):
            record = decision.get("decision_record") or {}
            if record.get("decision") in {"revoke", "reduce"}:
                remediation_queue.append({"review_id":review.get("review_id"),"review_assignment_id":decision.get("review_assignment_id"),"review_decision_id":decision.get("review_decision_id"),"decision":record.get("decision"),"retained_permissions":record.get("retained_permissions") or [],"reason":record.get("reason"),"remediation_status":"pending","source_event_sha256":decision.get("review_event_sha256")})
    expired = _expired_rules(rules)
    excessive = _excessive_access_findings(roles, rules)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "reviews": reviews,
        "open_reviews": open_reviews,
        "closed_reviews": closed_reviews,
        "review_count": len(reviews),
        "open_review_count": len(open_reviews),
        "closed_review_count": len(closed_reviews),
        "pending_assignments": pending_assignments,
        "pending_assignment_count": len(pending_assignments),
        "decision_counts": dict(sorted(decision_counts.items())),
        "certification_decisions": decisions,
        "certification_decision_count": len(decisions),
        "expired_access_findings": expired,
        "expired_access_finding_count": len(expired),
        "excessive_access_findings": excessive,
        "excessive_access_finding_count": len(excessive),
        "remediation_queue": remediation_queue,
        "remediation_queue_count": len(remediation_queue),
        "decision_options": list(DECISIONS),
        "access_review_history": events[-250:],
        "access_review_event_count": len(events),
        "review_decisions_mutate_access_policy": False,
        "remediation_requires_separate_policy_action": True,
        "case_access_scope_changed_by_review": False,
        "next_action": "review_access_certifications_and_remediation",
    }
