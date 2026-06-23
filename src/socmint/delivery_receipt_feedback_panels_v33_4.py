from __future__ import annotations

from typing import Any

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .delivery_attempt_receipt_ledger_v32_4 import (
    delivery_attempt_history,
    delivery_receipt_history,
)
from .dossier_assembly_workspace_v21_0 import _sha
from .recipient_feedback_correction_intake_v32_5 import (
    correction_intake_history,
    recipient_feedback_history,
)

SCHEMA = "socmint.delivery_receipt_feedback_panels.v33_4"
VERSION = "v33.4.0"
SENSITIVE_KEY_FRAGMENTS = (
    "endpoint",
    "contact_secret",
    "credential",
    "password",
    "token",
)
PANEL_STAGES = {
    "delivery": {"delivery"},
    "receipt": {"receipt"},
    "feedback": {"feedback"},
    "correction": {"feedback", "correction"},
}


def _for_case(rows: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("case_id") or "") == case_id]


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _panel_items(
    payload: dict[str, Any], key: str, stages: set[str]
) -> list[dict[str, Any]]:
    return [
        _sanitize(item)
        for item in payload.get(key) or []
        if str(item.get("stage") or "") in stages
    ]


def _panel(
    *,
    panel_name: str,
    case_id: str,
    records: list[dict[str, Any]],
    current: dict[str, Any] | None,
    snapshot: dict[str, Any],
    queue: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    stages = PANEL_STAGES[panel_name]
    content = {
        "panel": panel_name,
        "case_id": case_id,
        "record_count": len(records),
        "current": _sanitize(current),
        "history": _sanitize(records),
        "state": _sanitize(state),
        "blockers": _panel_items(snapshot, "blockers", stages),
        "available_actions": _panel_items(queue, "action_queue", stages),
        "read_only": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "source_records_mutated": False,
        "sensitive_values_rendered": False,
    }
    return {**content, "panel_sha256": _sha(content)}


def _feedback_resolution_state(
    feedback: list[dict[str, Any]], corrections: list[dict[str, Any]]
) -> tuple[list[str], list[str]]:
    corrected_ids = {
        str(item.get("recipient_feedback_id") or "")
        for item in corrections
        if item.get("recipient_feedback_id")
    }
    unresolved = [
        str(item.get("recipient_feedback_id") or "")
        for item in feedback
        if item.get("correction_review_required") is True
        and str(item.get("recipient_feedback_id") or "") not in corrected_ids
    ]
    resolved = [
        str(item.get("recipient_feedback_id") or "")
        for item in feedback
        if str(item.get("recipient_feedback_id") or "") in corrected_ids
    ]
    return unresolved, resolved


def _feedback_type(item: dict[str, Any]) -> str:
    return str((item.get("feedback_payload") or {}).get("feedback_type") or "")


def _acknowledges_receipt(
    item: dict[str, Any], delivery_receipt_id: str
) -> bool:
    return (
        _feedback_type(item) == "acknowledgement"
        and str(item.get("delivery_receipt_id") or "") == delivery_receipt_id
    )


def build_case_delivery_receipt_feedback_panels(case_id: str) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    snapshot = build_case_governance_snapshot(case_id)
    if snapshot.get("status") == "blocked":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": snapshot.get("case_id") or "",
            "panels": {},
            "blockers": snapshot.get("blockers") or [],
            "read_only": True,
            "actions_executed": False,
            "source_records_mutated": False,
        }

    queue = build_case_action_queue(case_id)
    attempts = _for_case(delivery_attempt_history(), case_id)
    receipts = _for_case(delivery_receipt_history(), case_id)
    feedback = _for_case(recipient_feedback_history(), case_id)
    corrections = _for_case(correction_intake_history(), case_id)
    current = snapshot.get("current") or {}
    unresolved_ids, resolved_ids = _feedback_resolution_state(feedback, corrections)

    current_attempt = current.get("delivery_attempt") or {}
    current_receipt = current.get("delivery_receipt") or {}
    current_feedback = current.get("recipient_feedback") or {}
    current_correction = current.get("correction_intake") or {}
    current_receipt_id = str(current_receipt.get("delivery_receipt_id") or "")

    panels = {
        "delivery": _panel(
            panel_name="delivery",
            case_id=case_id,
            records=attempts,
            current=current.get("delivery_attempt"),
            snapshot=snapshot,
            queue=queue,
            state={
                "attempt_count": len(attempts),
                "accepted_count": sum(
                    item.get("attempt_result") == "accepted" for item in attempts
                ),
                "failed_count": sum(
                    item.get("attempt_result") == "failed" for item in attempts
                ),
                "blocked_count": sum(
                    item.get("attempt_result") == "blocked" for item in attempts
                ),
                "current_result": current_attempt.get("attempt_result"),
                "receipt_required": bool(current_attempt) and not bool(current_receipt),
            },
        ),
        "receipt": _panel(
            panel_name="receipt",
            case_id=case_id,
            records=receipts,
            current=current.get("delivery_receipt"),
            snapshot=snapshot,
            queue=queue,
            state={
                "receipt_count": len(receipts),
                "delivered_count": sum(
                    item.get("delivery_result") == "delivered" for item in receipts
                ),
                "failed_count": sum(
                    item.get("delivery_result") == "failed" for item in receipts
                ),
                "pending_count": sum(
                    item.get("delivery_result") == "pending" for item in receipts
                ),
                "current_result": current_receipt.get("delivery_result"),
                "acknowledgement_required": (
                    current_receipt.get("acknowledgement_required") is True
                ),
                "acknowledgement_verified": bool(current_receipt_id)
                and any(
                    _acknowledges_receipt(item, current_receipt_id)
                    for item in feedback
                ),
            },
        ),
        "feedback": _panel(
            panel_name="feedback",
            case_id=case_id,
            records=feedback,
            current=current.get("recipient_feedback"),
            snapshot=snapshot,
            queue=queue,
            state={
                "feedback_count": len(feedback),
                "current_type": _feedback_type(current_feedback),
                "current_severity": (
                    current_feedback.get("feedback_payload") or {}
                ).get("severity"),
                "unresolved_feedback_ids": unresolved_ids,
                "resolved_feedback_ids": resolved_ids,
                "unresolved_count": len(unresolved_ids),
            },
        ),
        "correction": _panel(
            panel_name="correction",
            case_id=case_id,
            records=corrections,
            current=current.get("correction_intake"),
            snapshot=snapshot,
            queue=queue,
            state={
                "correction_count": len(corrections),
                "current_action": (
                    current_correction.get("correction_review") or {}
                ).get("correction_action"),
                "new_revision_review_count": sum(
                    (item.get("correction_review") or {}).get(
                        "correction_action"
                    )
                    == "new_revision_review"
                    for item in corrections
                ),
                "recall_review_count": sum(
                    (item.get("correction_review") or {}).get(
                        "correction_action"
                    )
                    == "recall_review"
                    for item in corrections
                ),
                "pending_action_count": sum(
                    item.get("correction_state")
                    == "intake_recorded_pending_action"
                    for item in corrections
                ),
            },
        ),
    }
    content = {
        "case_id": case_id,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "queue_summary_sha256": queue.get("queue_summary_sha256"),
        "panels": panels,
        "panel_order": ["delivery", "receipt", "feedback", "correction"],
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": (
            "attention_required"
            if any(panel.get("blockers") for panel in panels.values())
            else "ready"
        ),
        **content,
        "panels_sha256": _sha(content),
        "read_only": True,
        "canonical_browser_api_read_model": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "source_records_mutated": False,
        "raw_endpoint_or_contact_secret_rendered": False,
        "next_action": (
            queue.get("next_action") or "review_delivery_receipt_feedback"
        ),
    }


def build_case_delivery_receipt_feedback_panel(
    case_id: str, panel_name: str
) -> dict[str, Any]:
    payload = build_case_delivery_receipt_feedback_panels(case_id)
    if payload.get("status") == "blocked":
        return payload
    panel_name = str(panel_name or "").strip().lower()
    panel = (payload.get("panels") or {}).get(panel_name)
    if panel is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": payload.get("case_id"),
            "panel": panel_name,
            "blockers": [{"key": "invalid_panel", "stage": "workspace"}],
            "read_only": True,
            "actions_executed": False,
            "source_records_mutated": False,
        }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if panel.get("blockers") else "ready",
        "case_id": payload.get("case_id"),
        "snapshot_sha256": payload.get("snapshot_sha256"),
        "queue_summary_sha256": payload.get("queue_summary_sha256"),
        **panel,
    }
