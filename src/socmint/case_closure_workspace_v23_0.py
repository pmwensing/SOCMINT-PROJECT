from __future__ import annotations

import json
import os
from typing import Any

from .dossier_delivery_recovery_controls_v22_5 import build_delivery_recovery_state
from .dossier_release_history_v22_6 import build_release_delivery_history

SCHEMA = "socmint.case_closure_workspace.v23_0"
VERSION = "v23.0.0"

DEFAULT_RETENTION_POLICIES = [
    {
        "policy_id": "standard_case_retention",
        "display_name": "Standard case retention",
        "retention_years": 7,
        "archive_class": "standard",
        "description": "Retain the closed case and its immutable audit history for seven years.",
    },
    {
        "policy_id": "extended_investigative_retention",
        "display_name": "Extended investigative retention",
        "retention_years": 15,
        "archive_class": "extended",
        "description": "Retain cases with continuing intelligence or evidentiary value for fifteen years.",
    },
    {
        "policy_id": "indefinite_legal_hold",
        "display_name": "Indefinite legal hold",
        "retention_years": None,
        "archive_class": "legal_hold",
        "description": "Preserve the case until an authorized legal-hold release is recorded.",
    },
]


def _retention_policies() -> list[dict[str, Any]]:
    raw = os.getenv("SOCMINT_CASE_RETENTION_POLICIES", "").strip()
    if not raw:
        return [dict(item) for item in DEFAULT_RETENTION_POLICIES]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return [dict(item) for item in DEFAULT_RETENTION_POLICIES]
    if not isinstance(value, list):
        return [dict(item) for item in DEFAULT_RETENTION_POLICIES]
    policies = [
        item for item in value if isinstance(item, dict) and item.get("policy_id")
    ]
    return policies or [dict(item) for item in DEFAULT_RETENTION_POLICIES]


def build_case_closure_workspace(case_id: str) -> dict[str, Any]:
    release_history = build_release_delivery_history(case_id)
    recovery_state = build_delivery_recovery_state(case_id)
    policies = _retention_policies()
    proposed_policy = policies[0] if policies else None

    blockers = [dict(item) for item in release_history.get("unresolved_actions") or []]
    if not release_history.get("closure_ready"):
        blockers.append({"key": "release_closure_readiness_required"})
    if recovery_state.get("delivery_failed") and recovery_state.get(
        "failed_delivery_review_required"
    ):
        blockers.append({"key": "failed_delivery_review_required"})
    if recovery_state.get("latest_recall_request") and not recovery_state.get(
        "latest_reissue_authorization"
    ):
        blockers.append({"key": "recall_or_reissue_resolution_required"})

    deduplicated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for blocker in blockers:
        key = str(blocker.get("key") or "unknown_closure_blocker")
        if key not in seen:
            seen.add(key)
            deduplicated.append({**blocker, "key": key})

    closure_eligible = release_history.get("closure_ready") is True and not deduplicated
    archive_ready = closure_eligible and proposed_policy is not None
    supervisor_actions = [
        {
            "action": "review_closure_readiness",
            "version": "v23.1",
            "available": True,
        },
        {
            "action": "record_supervisor_closure_decision",
            "version": "v23.2",
            "available": closure_eligible,
        },
        {
            "action": "assign_retention_policy",
            "version": "v23.3",
            "available": closure_eligible,
        },
        {
            "action": "generate_archive_package",
            "version": "v23.4",
            "available": archive_ready,
        },
        {
            "action": "request_or_authorize_reopen",
            "version": "v23.5",
            "available": False,
        },
    ]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "eligible_for_closure_review" if closure_eligible else "blocked",
        "current_release_outcome": release_history.get("current_release_outcome"),
        "closure_eligible": closure_eligible,
        "archive_ready": archive_ready,
        "blocker_count": len(deduplicated),
        "blockers": deduplicated,
        "release_history": release_history,
        "delivery_recovery_state": recovery_state,
        "retention_policies": policies,
        "proposed_retention_policy": proposed_policy,
        "supervisor_actions": supervisor_actions,
        "links": {
            "release_workspace": f"/dossier-release/{case_id}",
            "release_history": f"/dossier-release/{case_id}/history",
            "case_delivery_workspace": f"/case-delivery?case_id={case_id}",
        },
        "source_records_mutated": False,
        "closure_record_created": False,
        "retention_assignment_created": False,
        "archive_package_created": False,
        "next_action": (
            "review_closure_readiness"
            if closure_eligible
            else deduplicated[0]["key"]
            if deduplicated
            else "complete_release_delivery_workflow"
        ),
    }
