from __future__ import annotations

from typing import Any

from . import database
from .audience_recipient_contract_v32_1 import audience_contract_history
from .authorization_policy_release_gate_v32_3 import authorization_decision_history
from .delivery_attempt_receipt_ledger_v32_4 import (
    delivery_attempt_history,
    delivery_receipt_history,
)
from .dissemination_package_v32_2 import (
    dissemination_package_history,
    find_dissemination_package,
)
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .recipient_feedback_correction_intake_v32_5 import (
    correction_intake_history,
    find_correction_intake,
    recipient_feedback_history,
)

SCHEMA = "socmint.recall_retention_lifecycle.v32_6"
VERSION = "v32.6.0"
RECALL_ACTION = "dissemination_recall_decision_recorded"
RETENTION_ACTION = "dissemination_retention_decision_recorded"
ALLOWED_RECALL_DECISIONS = {"initiate", "confirm", "deny", "lift"}
ALLOWED_RETENTION_DISPOSITIONS = {
    "retain",
    "legal_hold",
    "archive",
    "expiry_review",
}


def blocked(key: str, **details: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "blocked",
        "blockers": [{"key": key, **details}],
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "feedback_mutated": False,
        "correction_intake_mutated": False,
        "historical_evidence_deleted": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }


def _history(action: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=action)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                **_json_details(row),
                "lifecycle_record_id": row.id,
                "recorded_by": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def recall_decision_history() -> list[dict[str, Any]]:
    return _history(RECALL_ACTION)


def retention_decision_history() -> list[dict[str, Any]]:
    return _history(RETENTION_ACTION)


def recalls_for_package(
    dissemination_package_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = recall_decision_history()
    if not dissemination_package_id:
        return rows
    return [
        row
        for row in rows
        if row.get("dissemination_package_id") == dissemination_package_id
    ]


def recalls_for_correction(
    correction_intake_id: str | None = None,
) -> list[dict[str, Any]]:
    rows = recall_decision_history()
    if not correction_intake_id:
        return rows
    return [
        row
        for row in rows
        if row.get("correction_intake_id") == correction_intake_id
    ]


def retentions_for_case(case_id: str | None = None) -> list[dict[str, Any]]:
    rows = retention_decision_history()
    if not case_id:
        return rows
    return [row for row in rows if row.get("case_id") == case_id]


def find_recall_decision(recall_decision_id: str) -> dict[str, Any] | None:
    for item in recall_decision_history():
        if item.get("recall_decision_id") == recall_decision_id:
            return item
    return None


def find_retention_decision(retention_decision_id: str) -> dict[str, Any] | None:
    for item in retention_decision_history():
        if item.get("retention_decision_id") == retention_decision_id:
            return item
    return None


def current_recall_state(dissemination_package_id: str) -> str:
    rows = recalls_for_package(dissemination_package_id)
    return str(rows[-1].get("recall_state") or "not_recalled") if rows else "not_recalled"


def current_retention_state(case_id: str) -> str:
    rows = retentions_for_case(case_id)
    return str(rows[-1].get("retention_state") or "unassigned") if rows else "unassigned"


def _record(
    *,
    actor: str,
    action: str,
    target_value: str,
    event: dict[str, Any],
    ip_address: str | None,
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=action,
            target_value=target_value,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "lifecycle_record_id": row.id,
            "recorded_by": actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_recall_decision(
    *,
    reviewer: str,
    correction_intake_id: str,
    decision: str,
    reason: str,
    confirmed: bool,
    effective_at: str = "",
    replacement_published_revision_id: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    correction_intake_id = str(correction_intake_id or "").strip()
    decision = str(decision or "").strip().lower()
    reason = str(reason or "").strip()
    effective_at = str(effective_at or "").strip()
    replacement_published_revision_id = str(
        replacement_published_revision_id or ""
    ).strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_recall_decision_confirmation_required")
    if decision not in ALLOWED_RECALL_DECISIONS:
        return blocked("invalid_recall_decision")
    if not reason:
        return blocked("recall_reason_required")

    correction = find_correction_intake(correction_intake_id)
    if correction is None:
        return blocked("recall_review_correction_intake_required")
    correction_review = correction.get("correction_review") or {}
    if correction.get("recall_review_required") is not True:
        return blocked("recall_review_correction_intake_required")
    if correction_review.get("correction_action") != "recall_review":
        return blocked("recall_review_correction_intake_required")

    package_id = str(correction.get("dissemination_package_id") or "")
    package = find_dissemination_package(package_id)
    if package is None:
        return blocked("dissemination_package_required")

    prior_state = current_recall_state(package_id)
    allowed_prior_states = {
        "initiate": {"not_recalled", "recall_denied", "recall_lifted"},
        "confirm": {"recall_pending"},
        "deny": {"recall_pending"},
        "lift": {"recalled"},
    }
    if prior_state not in allowed_prior_states[decision]:
        return blocked(
            "invalid_recall_state_transition",
            decision=decision,
            prior_state=prior_state,
        )

    recall_state = {
        "initiate": "recall_pending",
        "confirm": "recalled",
        "deny": "recall_denied",
        "lift": "recall_lifted",
    }[decision]
    binding = {
        "case_id": package.get("case_id"),
        "correction_intake_id": correction_intake_id,
        "correction_intake_sha256": correction.get("correction_intake_sha256"),
        "recipient_feedback_id": correction.get("recipient_feedback_id"),
        "dissemination_package_id": package_id,
        "dissemination_package_sha256": package.get(
            "dissemination_package_sha256"
        ),
        "published_revision_id": package.get("published_revision_id"),
        "published_revision_sha256": package.get("published_revision_sha256"),
        "prior_recall_state": prior_state,
    }
    decision_payload = {
        "decision": decision,
        "reason": reason,
        "effective_at": effective_at,
        "replacement_published_revision_id": replacement_published_revision_id,
        "note": note,
    }
    content = {
        "event_type": RECALL_ACTION,
        "case_id": package.get("case_id"),
        "correction_intake_id": correction_intake_id,
        "recipient_feedback_id": correction.get("recipient_feedback_id"),
        "dissemination_package_id": package_id,
        "published_revision_id": package.get("published_revision_id"),
        "decision": decision,
        "prior_recall_state": prior_state,
        "recall_state": recall_state,
        "recall_binding": binding,
        "recall_binding_sha256": _sha(binding),
        "recall_decision": decision_payload,
        "recall_decision_payload_sha256": _sha(decision_payload),
        "historical_evidence_preserved": True,
        "future_delivery_blocked": recall_state in {"recall_pending", "recalled"},
        "recipient_notice_required": decision in {"initiate", "confirm", "lift"},
        "notice_transmitted_by_lifecycle_ledger": False,
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "feedback_mutated": False,
        "correction_intake_mutated": False,
        "historical_evidence_deleted": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "recall_decision_id": f"recall-decision-{digest[:24]}",
        "recall_decision_sha256": digest,
    }
    if any(
        item.get("recall_decision_sha256") == digest
        for item in recall_decision_history()
    ):
        return blocked("recall_decision_already_exists")

    result = _record(
        actor=reviewer,
        action=RECALL_ACTION,
        target_value=event["recall_decision_id"],
        event=event,
        ip_address=ip_address,
    )
    next_action = {
        "initiate": "confirm_or_deny_recall",
        "confirm": "record_recipient_recall_notices",
        "deny": "continue_retention_governance",
        "lift": "review_reissue_or_new_dissemination_package",
    }[decision]
    return {
        **result,
        "status": "recall_decision_recorded",
        "next_action": next_action,
    }


def record_retention_decision(
    *,
    reviewer: str,
    case_id: str,
    disposition: str,
    policy_id: str,
    reason: str,
    confirmed: bool,
    review_at: str = "",
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    disposition = str(disposition or "").strip().lower()
    policy_id = str(policy_id or "").strip()
    reason = str(reason or "").strip()
    review_at = str(review_at or "").strip()
    note = str(note or "").strip()

    if confirmed is not True:
        return blocked("explicit_retention_decision_confirmation_required")
    if not case_id:
        return blocked("case_id_required")
    if disposition not in ALLOWED_RETENTION_DISPOSITIONS:
        return blocked("invalid_retention_disposition")
    if not policy_id:
        return blocked("retention_policy_id_required")
    if not reason:
        return blocked("retention_reason_required")
    if disposition == "expiry_review" and not review_at:
        return blocked("retention_review_at_required")

    prior_state = current_retention_state(case_id)
    binding = {
        "case_id": case_id,
        "policy_id": policy_id,
        "prior_retention_state": prior_state,
        "recall_decision_ids": [
            row.get("recall_decision_id")
            for row in recall_decision_history()
            if row.get("case_id") == case_id
        ],
    }
    decision_payload = {
        "disposition": disposition,
        "policy_id": policy_id,
        "reason": reason,
        "review_at": review_at,
        "note": note,
    }
    retention_state = {
        "retain": "retained",
        "legal_hold": "legal_hold",
        "archive": "archived",
        "expiry_review": "expiry_review_scheduled",
    }[disposition]
    content = {
        "event_type": RETENTION_ACTION,
        "case_id": case_id,
        "disposition": disposition,
        "prior_retention_state": prior_state,
        "retention_state": retention_state,
        "retention_binding": binding,
        "retention_binding_sha256": _sha(binding),
        "retention_decision": decision_payload,
        "retention_decision_payload_sha256": _sha(decision_payload),
        "policy_bound": True,
        "legal_hold_active": disposition == "legal_hold",
        "destructive_action_performed": False,
        "historical_evidence_preserved": True,
        "source_intelligence_mutated": False,
        "published_revision_mutated": False,
        "package_mutated": False,
        "authorization_decision_mutated": False,
        "delivery_attempt_mutated": False,
        "delivery_receipt_mutated": False,
        "feedback_mutated": False,
        "correction_intake_mutated": False,
        "historical_evidence_deleted": False,
        "external_transmission_performed": False,
        "contact_secret_stored": False,
    }
    digest = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "retention_decision_id": f"retention-decision-{digest[:24]}",
        "retention_decision_sha256": digest,
    }
    if any(
        item.get("retention_decision_sha256") == digest
        for item in retention_decision_history()
    ):
        return blocked("retention_decision_already_exists")

    result = _record(
        actor=reviewer,
        action=RETENTION_ACTION,
        target_value=event["retention_decision_id"],
        event=event,
        ip_address=ip_address,
    )
    return {
        **result,
        "status": "retention_decision_recorded",
        "next_action": (
            "perform_product_review_and_browser_e2e_checkpoint"
            if disposition in {"retain", "archive"}
            else "monitor_retention_policy"
        ),
    }


def _event_time(item: dict[str, Any]) -> str:
    for key in (
        "recorded_at",
        "assembled_at",
        "decided_at",
        "published_at",
        "created_at",
    ):
        value = item.get(key)
        if value:
            return str(value)
    return ""


def _lifecycle_event(
    stage: str,
    item: dict[str, Any],
    source_id_key: str,
) -> dict[str, Any]:
    return {
        "lifecycle_stage": stage,
        "case_id": item.get("case_id"),
        "source_record_id": item.get(source_id_key),
        "source_record_sha256": item.get(f"{source_id_key}_sha256"),
        "event_time": _event_time(item),
        "event": item,
    }


def lifecycle_history(case_id: str | None = None) -> list[dict[str, Any]]:
    groups = [
        ("audience_contract", audience_contract_history(), "audience_contract_id"),
        ("dissemination_package", dissemination_package_history(), "dissemination_package_id"),
        ("authorization_decision", authorization_decision_history(), "authorization_decision_id"),
        ("delivery_attempt", delivery_attempt_history(), "delivery_attempt_id"),
        ("delivery_receipt", delivery_receipt_history(), "delivery_receipt_id"),
        ("recipient_feedback", recipient_feedback_history(), "recipient_feedback_id"),
        ("correction_intake", correction_intake_history(), "correction_intake_id"),
        ("recall_decision", recall_decision_history(), "recall_decision_id"),
        ("retention_decision", retention_decision_history(), "retention_decision_id"),
    ]
    events = [
        _lifecycle_event(stage, item, source_id_key)
        for stage, rows, source_id_key in groups
        for item in rows
        if not case_id or item.get("case_id") == case_id
    ]
    events.sort(
        key=lambda item: (
            str(item.get("event_time") or ""),
            str(item.get("lifecycle_stage") or ""),
            str(item.get("source_record_id") or ""),
        )
    )
    return events


def lifecycle_snapshot(case_id: str) -> dict[str, Any]:
    events = lifecycle_history(case_id)
    stage_counts: dict[str, int] = {}
    package_ids: set[str] = set()
    recipient_ids: set[str] = set()
    for item in events:
        stage = str(item.get("lifecycle_stage") or "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        event = item.get("event") or {}
        package_id = event.get("dissemination_package_id")
        recipient_id = event.get("recipient_id")
        if package_id:
            package_ids.add(str(package_id))
        if recipient_id:
            recipient_ids.add(str(recipient_id))

    recalled_packages = sorted(
        package_id
        for package_id in package_ids
        if current_recall_state(package_id) in {"recall_pending", "recalled"}
    )
    snapshot = {
        "schema": "socmint.lifecycle_snapshot.v32_6",
        "version": VERSION,
        "case_id": case_id,
        "event_count": len(events),
        "stage_counts": stage_counts,
        "package_count": len(package_ids),
        "recipient_count": len(recipient_ids),
        "recalled_package_ids": recalled_packages,
        "retention_state": current_retention_state(case_id),
        "historical_evidence_preserved": True,
        "source_records_mutated": False,
    }
    return {
        **snapshot,
        "lifecycle_snapshot_sha256": _sha(snapshot),
    }
