from __future__ import annotations

from typing import Any

from .audience_recipient_contract_v32_1 import audience_contract_history
from .authorization_policy_release_gate_v32_3 import authorization_decision_history
from .delivery_attempt_receipt_ledger_v32_4 import (
    delivery_attempt_history,
    delivery_receipt_history,
)
from .dissemination_package_v32_2 import dissemination_package_history
from .dossier_assembly_workspace_v21_0 import _sha
from .recipient_feedback_correction_intake_v32_5 import (
    correction_intake_history,
    recipient_feedback_history,
)
from .recall_retention_lifecycle_v32_6 import (
    current_recall_state,
    current_retention_state,
    lifecycle_snapshot,
    recall_decision_history,
    retention_decision_history,
)

SCHEMA = "socmint.case_governance_snapshot.v33_1"
VERSION = "v33.1.0"


def _for_case(rows: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("case_id") or "") == case_id]


def _latest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[-1] if rows else None


def _approved(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in decisions
        if item.get("result_status") == "approved_for_delivery_attempt"
        or item.get("status") == "approved_for_delivery_attempt"
    ]


def _delivered(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in receipts if item.get("delivery_result") == "delivered"]


def _open_feedback(
    feedback: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    corrected_ids = {
        str(item.get("recipient_feedback_id") or "")
        for item in corrections
        if item.get("recipient_feedback_id")
    }
    return [
        item
        for item in feedback
        if item.get("correction_review_required") is True
        and str(item.get("recipient_feedback_id") or "") not in corrected_ids
    ]


def _open_recall_reviews(
    corrections: list[dict[str, Any]],
    recalls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recalled_ids = {
        str(item.get("correction_intake_id") or "")
        for item in recalls
        if item.get("correction_intake_id")
    }
    return [
        item
        for item in corrections
        if item.get("recall_review_required") is True
        and str(item.get("correction_intake_id") or "") not in recalled_ids
    ]


def _blockers(
    *,
    audiences: list[dict[str, Any]],
    packages: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    open_feedback: list[dict[str, Any]],
    open_recalls: list[dict[str, Any]],
    retention_state: str,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if not audiences:
        blockers.append({"key": "audience_contract_required", "stage": "audience"})
    if audiences and not packages:
        blockers.append({"key": "dissemination_package_required", "stage": "package"})
    if packages and not approvals:
        blockers.append({"key": "authorization_approval_required", "stage": "authorization"})
    if approvals and not attempts:
        blockers.append({"key": "delivery_attempt_required", "stage": "delivery"})
    if attempts and not receipts:
        blockers.append({"key": "delivery_receipt_required", "stage": "receipt"})
    if open_feedback:
        blockers.append({"key": "correction_review_required", "stage": "feedback"})
    if open_recalls:
        blockers.append({"key": "recall_decision_required", "stage": "recall"})
    if retention_state == "unassigned":
        blockers.append({"key": "retention_decision_required", "stage": "retention"})
    return blockers


def _next_actions(blockers: list[dict[str, str]]) -> list[str]:
    actions = {
        "audience_contract_required": "create_audience_contract",
        "dissemination_package_required": "assemble_dissemination_package",
        "authorization_approval_required": "record_authorization_policy_decision",
        "delivery_attempt_required": "record_delivery_attempt",
        "delivery_receipt_required": "record_delivery_receipt",
        "correction_review_required": "record_correction_intake",
        "recall_decision_required": "record_recall_decision",
        "retention_decision_required": "record_retention_decision",
    }
    return [actions[item["key"]] for item in blockers if item["key"] in actions]


def build_case_governance_snapshot(case_id: str) -> dict[str, Any]:
    case_id = str(case_id or "").strip()
    if not case_id:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": "",
            "blockers": [{"key": "case_id_required", "stage": "case"}],
            "safe_next_actions": [],
            "read_only": True,
            "source_records_mutated": False,
        }

    audiences = _for_case(audience_contract_history(), case_id)
    packages = _for_case(dissemination_package_history(), case_id)
    decisions = _for_case(authorization_decision_history(), case_id)
    attempts = _for_case(delivery_attempt_history(), case_id)
    receipts = _for_case(delivery_receipt_history(), case_id)
    feedback = _for_case(recipient_feedback_history(), case_id)
    corrections = _for_case(correction_intake_history(), case_id)
    recalls = _for_case(recall_decision_history(), case_id)
    retentions = _for_case(retention_decision_history(), case_id)

    approvals = _approved(decisions)
    delivered = _delivered(receipts)
    unresolved_feedback = _open_feedback(feedback, corrections)
    unresolved_recalls = _open_recall_reviews(corrections, recalls)
    retention_state = current_retention_state(case_id)
    package_ids = [
        str(item.get("dissemination_package_id") or "")
        for item in packages
        if item.get("dissemination_package_id")
    ]
    recalled_packages = [
        package_id
        for package_id in package_ids
        if current_recall_state(package_id) in {"recall_pending", "recalled"}
    ]
    blockers = _blockers(
        audiences=audiences,
        packages=packages,
        approvals=approvals,
        attempts=attempts,
        receipts=receipts,
        open_feedback=unresolved_feedback,
        open_recalls=unresolved_recalls,
        retention_state=retention_state,
    )
    safe_next_actions = _next_actions(blockers)
    lifecycle = lifecycle_snapshot(case_id)

    read_model = {
        "case_id": case_id,
        "counts": {
            "audience_contracts": len(audiences),
            "dissemination_packages": len(packages),
            "authorization_decisions": len(decisions),
            "approved_authorizations": len(approvals),
            "delivery_attempts": len(attempts),
            "delivery_receipts": len(receipts),
            "delivered_receipts": len(delivered),
            "recipient_feedback": len(feedback),
            "correction_intakes": len(corrections),
            "recall_decisions": len(recalls),
            "retention_decisions": len(retentions),
        },
        "current": {
            "audience_contract": _latest(audiences),
            "dissemination_package": _latest(packages),
            "authorization_decision": _latest(decisions),
            "delivery_attempt": _latest(attempts),
            "delivery_receipt": _latest(receipts),
            "recipient_feedback": _latest(feedback),
            "correction_intake": _latest(corrections),
            "recall_decision": _latest(recalls),
            "retention_decision": _latest(retentions),
        },
        "state": {
            "retention_state": retention_state,
            "recalled_package_ids": recalled_packages,
            "open_feedback_ids": [
                item.get("recipient_feedback_id") for item in unresolved_feedback
            ],
            "open_recall_correction_ids": [
                item.get("correction_intake_id") for item in unresolved_recalls
            ],
        },
        "blockers": blockers,
        "safe_next_actions": safe_next_actions,
        "lifecycle_snapshot": lifecycle,
    }
    snapshot_hash = _sha(read_model)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if blockers else "ready",
        **read_model,
        "snapshot_sha256": snapshot_hash,
        "read_only": True,
        "canonical_browser_api_read_model": True,
        "v32_contracts_remain_authoritative": True,
        "source_records_mutated": False,
        "raw_endpoint_or_contact_secret_rendered": False,
        "next_action": safe_next_actions[0] if safe_next_actions else "review_case_governance",
    }
