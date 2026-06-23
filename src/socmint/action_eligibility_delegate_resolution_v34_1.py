from __future__ import annotations

from typing import Any

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.action_eligibility_delegate_resolution.v34_1"
VERSION = "v34.1.1"

DELEGATE_REGISTRY: dict[str, dict[str, Any]] = {
    "create_audience_contract": {
        "delegate_service": (
            "audience_recipient_contract_v32_1."
            "record_audience_recipient_contract"
        ),
        "required_targets": (),
    },
    "assemble_dissemination_package": {
        "delegate_service": (
            "dissemination_package_v32_2.assemble_dissemination_package"
        ),
        "required_targets": ("audience_contract_id",),
    },
    "record_authorization_policy_decision": {
        "delegate_service": (
            "authorization_policy_release_gate_v32_3."
            "record_authorization_policy_decision"
        ),
        "required_targets": ("dissemination_package_id",),
    },
    "record_delivery_attempt": {
        "delegate_service": (
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_attempt"
        ),
        "required_targets": (
            "dissemination_package_id",
            "authorization_decision_id",
        ),
    },
    "record_delivery_receipt": {
        "delegate_service": (
            "delivery_attempt_receipt_ledger_v32_4.record_delivery_receipt"
        ),
        "required_targets": ("delivery_attempt_id",),
    },
    "record_correction_intake": {
        "delegate_service": (
            "recipient_feedback_correction_intake_v32_5."
            "record_correction_intake"
        ),
        "required_targets": ("recipient_feedback_id",),
    },
    "record_recall_decision": {
        "delegate_service": (
            "recall_retention_lifecycle_v32_6.record_recall_decision"
        ),
        "required_targets": ("correction_intake_id",),
    },
    "record_retention_decision": {
        "delegate_service": (
            "recall_retention_lifecycle_v32_6.record_retention_decision"
        ),
        "required_targets": (),
    },
}


def _missing_targets(
    targets: dict[str, Any], required_targets: tuple[str, ...]
) -> list[str]:
    return [
        key
        for key in required_targets
        if targets.get(key) in (None, "", [], {})
    ]


def _resolve_item(item: dict[str, Any]) -> dict[str, Any]:
    action = str(item.get("action") or "")
    registered = DELEGATE_REGISTRY.get(action)
    blockers: list[dict[str, str]] = []

    if registered is None:
        blockers.append(
            {
                "key": "unregistered_action",
                "message": "The action is not registered for v34 execution.",
            }
        )
        delegate_service = str(item.get("delegate_service") or "")
        required_targets: tuple[str, ...] = ()
    else:
        delegate_service = str(registered["delegate_service"])
        required_targets = tuple(registered["required_targets"])
        if item.get("delegate_service") != delegate_service:
            blockers.append(
                {
                    "key": "delegate_service_mismatch",
                    "message": (
                        "The queue delegate does not match the authoritative "
                        "v34 registry."
                    ),
                }
            )

    targets = dict(item.get("targets") or {})
    missing = _missing_targets(targets, required_targets)
    if missing:
        blockers.append(
            {
                "key": "required_target_missing",
                "message": "Required action targets are missing: "
                + ", ".join(sorted(missing)),
            }
        )
    if item.get("confirmation_required") is not True:
        blockers.append(
            {
                "key": "explicit_confirmation_not_required",
                "message": "Mutating actions must require explicit confirmation.",
            }
        )
    if item.get("automatic_execution_allowed") is not False:
        blockers.append(
            {
                "key": "automatic_execution_not_disabled",
                "message": "Automatic execution must remain disabled.",
            }
        )

    content = {
        "case_id": item.get("case_id"),
        "action_queue_item_id": item.get("action_queue_item_id"),
        "action": action,
        "stage": item.get("stage"),
        "priority": item.get("priority"),
        "severity": item.get("severity"),
        "delegate_service": delegate_service,
        "delegate_module": (
            delegate_service.rsplit(".", 1)[0] if "." in delegate_service else ""
        ),
        "delegate_function": (
            delegate_service.rsplit(".", 1)[1] if "." in delegate_service else ""
        ),
        "targets": targets,
        "required_targets": list(required_targets),
        "missing_targets": sorted(missing),
        "confirmation_required": True,
        "automatic_execution_allowed": False,
        "eligible": not blockers,
        "eligibility_blockers": blockers,
        "execution_performed": False,
    }
    digest = _sha(content)
    return {
        **content,
        "eligibility_resolution_id": f"eligibility-{digest[:24]}",
        "eligibility_resolution_sha256": digest,
    }


def build_action_eligibility_delegate_resolution(case_id: str) -> dict[str, Any]:
    queue = build_case_action_queue(case_id)
    if queue.get("status") == "blocked":
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": queue.get("case_id") or case_id,
            "action_queue_sha256": queue.get("queue_summary_sha256"),
            "resolutions": [],
            "blockers": queue.get("blockers") or [],
            "read_only": True,
            "execution_performed": False,
            "source_records_mutated": False,
        }

    resolutions = [
        _resolve_item(item) for item in queue.get("action_queue") or []
    ]
    resolutions.sort(
        key=lambda item: (
            int(item.get("priority") or 0),
            str(item.get("action") or ""),
        )
    )
    summary = {
        "case_id": queue.get("case_id") or case_id,
        "queue_summary_sha256": queue.get("queue_summary_sha256"),
        "resolution_count": len(resolutions),
        "eligible_count": sum(1 for item in resolutions if item["eligible"]),
        "blocked_count": sum(1 for item in resolutions if not item["eligible"]),
        "next_eligible_action": next(
            (
                item["action"]
                for item in resolutions
                if item.get("eligible") is True
            ),
            "review_case_governance",
        ),
    }
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": (
            "ready_for_confirmation"
            if summary["eligible_count"]
            else "review_required"
        ),
        **summary,
        "resolution_summary_sha256": _sha(summary),
        "resolutions": resolutions,
        "read_only": True,
        "eligibility_only": True,
        "execution_performed": False,
        "source_records_mutated": False,
        "v32_services_authoritative": True,
        "v33_queue_is_source": True,
        "human_confirmation_required_before_execution": True,
        "raw_endpoint_or_contact_secret_rendered": False,
    }
