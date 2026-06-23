from __future__ import annotations

from typing import Any

from .action_queue_blocker_surface_v33_2 import build_case_action_queue
from .audience_recipient_contract_v32_1 import audience_contract_history
from .authorization_policy_release_gate_v32_3 import authorization_decision_history
from .case_governance_snapshot_v33_1 import build_case_governance_snapshot
from .dissemination_package_v32_2 import dissemination_package_history
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.audience_package_authorization_panels.v33_3"
VERSION = "v33.3.0"
SENSITIVE_KEY_FRAGMENTS = (
    "endpoint",
    "contact_secret",
    "credential",
    "password",
    "access_token",
    "refresh_token",
)
PANEL_STAGES = {
    "audience": {"audience"},
    "package": {"package"},
    "authorization": {"authorization"},
}


def _for_case(rows: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("case_id") or "") == case_id]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if not any(fragment in key.lower() for fragment in SENSITIVE_KEY_FRAGMENTS)
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _panel_actions(queue: dict[str, Any], stages: set[str]) -> list[dict[str, Any]]:
    return [
        _sanitize(item)
        for item in queue.get("action_queue") or []
        if str(item.get("stage") or "") in stages
    ]


def _panel_blockers(snapshot: dict[str, Any], stages: set[str]) -> list[dict[str, Any]]:
    return [
        _sanitize(item)
        for item in snapshot.get("blockers") or []
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
        "blockers": _panel_blockers(snapshot, stages),
        "available_actions": _panel_actions(queue, stages),
        "read_only": True,
        "actions_executed": False,
        "actions_delegate_to_v32_services": True,
        "human_confirmation_required": True,
        "source_records_mutated": False,
        "sensitive_values_rendered": False,
    }
    return {
        **content,
        "panel_sha256": _sha(content),
    }


def build_case_audience_package_authorization_panels(
    case_id: str,
) -> dict[str, Any]:
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
    audiences = _for_case(audience_contract_history(), case_id)
    packages = _for_case(dissemination_package_history(), case_id)
    decisions = _for_case(authorization_decision_history(), case_id)
    current = snapshot.get("current") or {}

    approved = [
        item
        for item in decisions
        if item.get("result_status") == "approved_for_delivery_attempt"
        or item.get("status") == "approved_for_delivery_attempt"
    ]
    denied = [
        item
        for item in decisions
        if item.get("result_status") == "release_denied"
        or item.get("status") == "release_denied"
    ]
    held = [
        item
        for item in decisions
        if item.get("result_status") == "release_held"
        or item.get("status") == "release_held"
    ]

    panels = {
        "audience": _panel(
            panel_name="audience",
            case_id=case_id,
            records=audiences,
            current=current.get("audience_contract"),
            snapshot=snapshot,
            queue=queue,
            state={
                "configured": bool(audiences),
                "recipient_count": len(
                    (
                        current.get("audience_contract") or {}
                    ).get("recipient_inventory")
                    or []
                ),
            },
        ),
        "package": _panel(
            panel_name="package",
            case_id=case_id,
            records=packages,
            current=current.get("dissemination_package"),
            snapshot=snapshot,
            queue=queue,
            state={
                "assembled": bool(packages),
                "active_package_id": (
                    current.get("dissemination_package") or {}
                ).get("dissemination_package_id"),
            },
        ),
        "authorization": _panel(
            panel_name="authorization",
            case_id=case_id,
            records=decisions,
            current=current.get("authorization_decision"),
            snapshot=snapshot,
            queue=queue,
            state={
                "decision_count": len(decisions),
                "approved_count": len(approved),
                "denied_count": len(denied),
                "held_count": len(held),
                "delivery_eligible": bool(approved),
            },
        ),
    }
    content = {
        "case_id": case_id,
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "queue_summary_sha256": queue.get("queue_summary_sha256"),
        "panels": panels,
        "panel_order": ["audience", "package", "authorization"],
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
            queue.get("next_action") or "review_audience_package_authorization"
        ),
    }


def build_case_governance_panel(case_id: str, panel_name: str) -> dict[str, Any]:
    payload = build_case_audience_package_authorization_panels(case_id)
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
