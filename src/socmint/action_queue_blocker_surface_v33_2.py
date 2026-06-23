from __future__ import annotations

from typing import Any

from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.action_queue_blocker_surface.v33_2"
VERSION = "v33.2.1"

ACTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "create_audience_contract": {
        "stage": "audience",
        "priority": 10,
        "severity": "high",
        "service": (
            "audience_recipient_contract_v32_1."
            "record_audience_recipient_contract"
        ),
        "confirmation_required": True,
        "rationale": (
            "A case-scoped audience and recipient contract is required "
            "before package assembly."
        ),
    },
    "assemble_dissemination_package": {
        "stage": "package",
        "priority": 20,
        "severity": "high",
        "service": (
            "dissemination_package_v32_2.assemble_dissemination_package"
        ),
        "confirmation_required": True,
        "rationale": (
            "An immutable published revision must be bound to the approved "
            "audience scope."
        ),
    },
    "record_authorization_policy_decision": {
        "stage": "authorization",
        "priority": 30,
        "severity": "critical",
        "service": (
            "authorization_policy_release_gate_v32_3."
            "record_authorization_policy_decision"
        ),
        "confirmation_required": True,
        "rationale": (
            "Human authorization and policy approval are required before "
            "delivery activity."
        ),
    },
    "record_delivery_attempt": {
        "stage": "delivery",
        "priority": 40,
        "severity": "high",
        "service": (
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
        ),
        "confirmation_required": True,
        "rationale": (
            "An approved package requires an append-only delivery-attempt "
            "record."
        ),
    },
    "record_delivery_receipt": {
        "stage": "receipt",
        "priority": 50,
        "severity": "medium",
        "service": (
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_receipt"
        ),
        "confirmation_required": True,
        "rationale": (
            "Delivery outcome evidence must be recorded without altering "
            "the attempt."
        ),
    },
    "record_correction_intake": {
        "stage": "feedback",
        "priority": 60,
        "severity": "high",
        "service": (
            "recipient_feedback_correction_intake_v32_5."
            "record_correction_intake"
        ),
        "confirmation_required": True,
        "rationale": (
            "Substantive recipient feedback requires explicit correction "
            "review."
        ),
    },
    "record_recall_decision": {
        "stage": "recall",
        "priority": 70,
        "severity": "critical",
        "service": (
            "recall_retention_lifecycle_v32_6.record_recall_decision"
        ),
        "confirmation_required": True,
        "rationale": (
            "A recall-review correction requires an explicit human recall "
            "decision."
        ),
    },
    "record_retention_decision": {
        "stage": "retention",
        "priority": 80,
        "severity": "medium",
        "service": (
            "recall_retention_lifecycle_v32_6.record_retention_decision"
        ),
        "confirmation_required": True,
        "rationale": (
            "The case requires a policy-bound retention disposition."
        ),
    },
}


def _first_identifier(values: Any) -> str | None:
    normalized = sorted(
        {str(value).strip() for value in (values or []) if str(value).strip()}
    )
    return normalized[0] if normalized else None


def _targets(snapshot: dict[str, Any], action: str) -> dict[str, Any]:
    current = snapshot.get("current") or {}
    state = snapshot.get("state") or {}
    mapping = {
        "create_audience_contract": {},
        "assemble_dissemination_package": {
            "audience_contract_id": (
                current.get("audience_contract") or {}
            ).get("audience_contract_id")
        },
        "record_authorization_policy_decision": {
            "dissemination_package_id": (
                current.get("dissemination_package") or {}
            ).get("dissemination_package_id")
        },
        "record_delivery_attempt": {
            "dissemination_package_id": (
                current.get("dissemination_package") or {}
            ).get("dissemination_package_id"),
            "authorization_decision_id": (
                current.get("authorization_decision") or {}
            ).get("authorization_decision_id"),
        },
        "record_delivery_receipt": {
            "delivery_attempt_id": (
                current.get("delivery_attempt") or {}
            ).get("delivery_attempt_id")
        },
        "record_correction_intake": {
            "recipient_feedback_id": _first_identifier(
                state.get("open_feedback_ids")
            )
        },
        "record_recall_decision": {
            "correction_intake_id": _first_identifier(
                state.get("open_recall_correction_ids")
            )
        },
        "record_retention_decision": {},
    }
    return {
        key: value
        for key, value in mapping.get(action, {}).items()
        if value not in (None, "", [])
    }


def build_case_action_queue(case_id: str) -> dict[str, Any]:
    snapshot = build_case_governance_snapshot(case_id)
    if snapshot.get("status") == "blocked":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": snapshot.get("case_id") or "",
            "snapshot_sha256": snapshot.get("snapshot_sha256"),
            "action_queue": [],
            "blockers": snapshot.get("blockers") or [],
            "read_only": True,
            "actions_executed": False,
            "source_records_mutated": False,
        }

    blocker_by_stage = {
        str(item.get("stage") or ""): item
        for item in snapshot.get("blockers") or []
    }
    queue = []
    for action in snapshot.get("safe_next_actions") or []:
        definition = ACTION_DEFINITIONS.get(action)
        if definition is None:
            continue
        stage = str(definition["stage"])
        blocker = blocker_by_stage.get(stage, {})
        content = {
            "case_id": snapshot.get("case_id"),
            "action": action,
            "stage": stage,
            "priority": definition["priority"],
            "severity": definition["severity"],
            "blocking": True,
            "blocker_key": blocker.get("key"),
            "rationale": definition["rationale"],
            "delegate_service": definition["service"],
            "confirmation_required": definition[
                "confirmation_required"
            ],
            "targets": _targets(snapshot, action),
            "automatic_execution_allowed": False,
        }
        digest = _sha(content)
        queue.append(
            {
                **content,
                "action_queue_item_id": (
                    f"action-queue-item-{digest[:24]}"
                ),
                "action_queue_item_sha256": digest,
            }
        )

    queue.sort(
        key=lambda item: (
            int(item.get("priority") or 0),
            str(item.get("action") or ""),
        )
    )
    summary = {
        "case_id": snapshot.get("case_id"),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "queue_count": len(queue),
        "critical_count": sum(
            1 for item in queue if item.get("severity") == "critical"
        ),
        "blocking_count": sum(
            1 for item in queue if item.get("blocking") is True
        ),
        "next_action": (
            queue[0]["action"] if queue else "review_case_governance"
        ),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "attention_required" if queue else "ready",
        **summary,
        "queue_summary_sha256": _sha(summary),
        "action_queue": queue,
        "blockers": snapshot.get("blockers") or [],
        "read_only": True,
        "decision_support_only": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "source_records_mutated": False,
        "raw_endpoint_or_contact_secret_rendered": False,
    }
