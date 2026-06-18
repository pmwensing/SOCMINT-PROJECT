from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

SCHEMA = "socmint.access_review_certification.v28_4"
VERSION = "v28.4.0"
ACTIONS = (
    "administration_access_review_created",
    "administration_access_review_assigned",
    "administration_access_review_decided",
    "administration_access_review_closed",
)
DECISIONS = ("certify", "revoke", "reduce", "defer")


def blocked(key: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key}],
        "access_policy_records_mutated": False,
        "case_access_scope_changed": False,
    }


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


def _record(action: str, actor: str, target: str, event: dict[str, Any], ip_address: str | None) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(actor=actor, action=action, target_value=target, ip_address=ip_address, details=_canonical(event))
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


def current_reviews() -> list[dict[str, Any]]:
    reviews: dict[str, dict[str, Any]] = {}
    for event in history():
        review_id = str(event.get("review_id") or "")
        if not review_id:
            continue
        if event.get("event_type") == "review_created":
            reviews[review_id] = {
                **event,
                "review_status": "open",
                "assignments": [],
                "decisions": [],
            }
        elif review_id in reviews:
            review = dict(reviews[review_id])
            if event.get("event_type") == "review_assigned":
                review["assignments"] = [*review.get("assignments", []), event]
            elif event.get("event_type") == "review_decided":
                review["decisions"] = [*review.get("decisions", []), event]
            elif event.get("event_type") == "review_closed":
                review["review_status"] = "closed"
                review["closed_event"] = event
            reviews[review_id] = review
    return sorted(reviews.values(), key=lambda item: str(item.get("created_at") or item.get("recorded_at") or ""))


def find_review(review_id: str) -> dict[str, Any] | None:
    return next((item for item in current_reviews() if item.get("review_id") == review_id), None)


def create_review(*, actor: str, name: str, scope: Any, due_at: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    name = str(name or "").strip()
    reason = str(reason or "").strip()
    normalized_scope = scope if isinstance(scope, dict) else {}
    if confirmed is not True:
        return blocked("explicit_access_review_creation_confirmation_required")
    if not name:
        return blocked("review_name_required")
    if not normalized_scope:
        return blocked("review_scope_required")
    if not reason:
        return blocked("administrative_reason_required")
    definition = {"name": name, "scope": normalized_scope, "due_at": str(due_at or "").strip()}
    content = {"event_type": "review_created", "definition": definition, "definition_sha256": _sha(definition), "reason": reason}
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "review_id": f"access-review-{digest[:24]}",
        "review_event_id": f"review-event-{digest[:24]}",
        "review_event_sha256": digest,
        "access_policy_records_mutated": False,
        "case_access_scope_changed": False,
    }
    result = _record(ACTIONS[0], actor, name, event, ip_address)
    return {**result, "status": "access_review_created", "next_action": "assign_access_review"}


def assign_review(review_id: str, *, actor: str, reviewer_username: str, subject_type: str, subject_id: str, case_id: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    review = find_review(review_id)
    if review is None or review.get("review_status") != "open":
        return blocked("open_access_review_required")
    reviewer_username = str(reviewer_username or "").strip()
    subject_type = str(subject_type or "").strip()
    subject_id = str(subject_id or "").strip()
    case_id = str(case_id or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_review_assignment_confirmation_required")
    if not reviewer_username:
        return blocked("reviewer_required")
    if subject_type not in {"user", "role"}:
        return blocked("review_subject_type_invalid")
    if not subject_id:
        return blocked("review_subject_required")
    if not reason:
        return blocked("administrative_reason_required")
    assignment = {"reviewer_username": reviewer_username, "subject_type": subject_type, "subject_id": subject_id, "case_id": case_id}
    content = {"event_type": "review_assigned", "review_id": review_id, "assignment": assignment, "assignment_sha256": _sha(assignment), "reason": reason}
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "review_assignment_id": f"review-assignment-{digest[:24]}", "review_event_id": f"review-event-{digest[:24]}", "review_event_sha256": digest, "access_policy_records_mutated": False, "case_access_scope_changed": False}
    result = _record(ACTIONS[1], actor, review_id, event, ip_address)
    return {**result, "status": "access_review_assigned", "next_action": "record_access_review_decision"}


def decide_review(review_id: str, *, actor: str, assignment_id: str, decision: str, retained_permissions: Any, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    review = find_review(review_id)
    if review is None or review.get("review_status") != "open":
        return blocked("open_access_review_required")
    assignment = next((item for item in review.get("assignments", []) if item.get("review_assignment_id") == assignment_id), None)
    if assignment is None:
        return blocked("review_assignment_required")
    decision = str(decision or "").strip()
    reason = str(reason or "").strip()
    if confirmed is not True:
        return blocked("explicit_review_decision_confirmation_required")
    if decision not in DECISIONS:
        return blocked("review_decision_invalid")
    if not reason:
        return blocked("decision_reason_required")
    prior = next((item for item in review.get("decisions", []) if item.get("review_assignment_id") == assignment_id), None)
    if prior is not None:
        return blocked("review_assignment_already_decided")
    normalized_permissions = sorted({str(item) for item in (retained_permissions or []) if str(item)})
    decision_record = {"decision": decision, "retained_permissions": normalized_permissions, "reason": reason}
    binding = {"review_assignment_id": assignment_id, "review_event_sha256": assignment.get("review_event_sha256"), "assignment_sha256": assignment.get("assignment_sha256")}
    content = {"event_type": "review_decided", "review_id": review_id, "review_assignment_id": assignment_id, "decision_record": decision_record, "decision_record_sha256": _sha(decision_record), "assignment_binding": binding, "assignment_binding_sha256": _sha(binding)}
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "review_decision_id": f"review-decision-{digest[:24]}", "review_event_id": f"review-event-{digest[:24]}", "review_event_sha256": digest, "remediation_required": decision in {"revoke", "reduce"}, "access_policy_records_mutated": False, "case_access_scope_changed": False}
    result = _record(ACTIONS[2], actor, review_id, event, ip_address)
    return {**result, "status": "access_review_decided", "next_action": "queue_access_remediation" if event["remediation_required"] else "review_access_certification"}


def close_review(review_id: str, *, actor: str, reason: str, confirmed: bool, ip_address: str | None = None) -> dict[str, Any]:
    review = find_review(review_id)
    if review is None or review.get("review_status") != "open":
        return blocked("open_access_review_required")
    if confirmed is not True:
        return blocked("explicit_review_closure_confirmation_required")
    reason = str(reason or "").strip()
    if not reason:
        return blocked("administrative_reason_required")
    assignments = review.get("assignments", [])
    decided_ids = {str(item.get("review_assignment_id")) for item in review.get("decisions", [])}
    unresolved = [item for item in assignments if str(item.get("review_assignment_id")) not in decided_ids]
    if unresolved:
        return blocked("all_review_assignments_must_be_decided")
    summary = {"assignment_count": len(assignments), "decision_count": len(decided_ids)}
    content = {"event_type": "review_closed", "review_id": review_id, "summary": summary, "summary_sha256": _sha(summary), "reason": reason}
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "review_event_id": f"review-event-{digest[:24]}", "review_event_sha256": digest, "access_policy_records_mutated": False, "case_access_scope_changed": False}
    result = _record(ACTIONS[3], actor, review_id, event, ip_address)
    return {**result, "status": "access_review_closed", "next_action": "archive_access_review"}
