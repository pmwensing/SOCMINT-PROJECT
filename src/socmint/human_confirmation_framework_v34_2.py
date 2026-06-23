from __future__ import annotations

from typing import Any

from .action_eligibility_delegate_resolution_v34_1 import (
    build_action_eligibility_delegate_resolution,
)
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.human_confirmation_framework.v34_2"
VERSION = "v34.2.0"


def build_confirmation_contract(
    case_id: str,
    action: str,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eligibility = build_action_eligibility_delegate_resolution(case_id)
    resolution = next(
        (
            item
            for item in eligibility.get("resolutions") or []
            if item.get("action") == action
        ),
        None,
    )
    if resolution is None or resolution.get("eligible") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": case_id,
            "action": action,
            "blockers": (
                (resolution or {}).get("eligibility_blockers")
                or [{"key": "action_not_eligible"}]
            ),
            "confirmation_accepted": False,
            "execution_performed": False,
        }
    content = {
        "case_id": case_id,
        "action": action,
        "delegate_service": resolution.get("delegate_service"),
        "eligibility_resolution_sha256": resolution.get(
            "eligibility_resolution_sha256"
        ),
        "targets": resolution.get("targets") or {},
        "inputs": inputs or {},
        "impact_summary": (
            f"Confirm {action} for case {case_id} using "
            f"{resolution.get('delegate_service')}"
        ),
    }
    digest = _sha(content)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "confirmation_required",
        **content,
        "confirmation_id": f"confirm-{digest[:32]}",
        "confirmation_sha256": digest,
        "confirmation_accepted": False,
        "execution_performed": False,
        "expires_on_state_change": True,
        "duplicate_submission_protection_required": True,
    }


def validate_confirmation(
    contract: dict[str, Any],
    confirmation_id: str,
    confirmed: bool,
) -> dict[str, Any]:
    accepted = (
        contract.get("status") == "confirmation_required"
        and confirmed is True
        and confirmation_id == contract.get("confirmation_id")
    )
    return {
        "accepted": accepted,
        "reason": "accepted" if accepted else "confirmation_invalid",
        "confirmation_sha256": contract.get("confirmation_sha256"),
    }
