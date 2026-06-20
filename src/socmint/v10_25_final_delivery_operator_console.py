from __future__ import annotations

from copy import deepcopy
from typing import Any

from .v10_24_final_delivery_workspace import build_final_delivery_workspace_from_request

OPERATOR_CONSOLE_SCHEMA = "socmint.v10_25.final_delivery_operator_console"
VERSION = "v10.25.0"

REQUIRED_CARD_TYPES = (
    "delivery_readiness",
    "package_inventory",
    "findings",
    "export_availability",
    "operator_next_action",
)


def readiness_for_workspace(workspace: dict[str, Any]) -> str:
    delivery_action = workspace.get("delivery_action")
    if delivery_action == "deliver_ready" and workspace.get("package_ready") is True:
        return "ready"
    if delivery_action == "human_review_required":
        return "review_required"
    return "blocked"


def allowed_actions_for_readiness(readiness: str) -> list[str]:
    if readiness == "ready":
        return ["review_final_package", "export_zip", "record_delivery"]
    if readiness == "review_required":
        return ["review_findings", "resolve_or_acknowledge"]
    return ["regenerate_v7_5_14_package", "rerun_verification"]


def blocked_actions_for_readiness(readiness: str) -> list[str]:
    if readiness == "ready":
        return []
    if readiness == "review_required":
        return ["record_delivery"]
    return ["export_zip", "record_delivery"]


def build_commands(readiness: str, workspace: dict[str, Any]) -> list[dict[str, Any]]:
    export_enabled = readiness == "ready" and workspace.get("package_ready") is True
    return [
        {
            "id": "review_final_package",
            "label": "Review final package",
            "enabled": readiness in {"ready", "review_required"},
            "route": "/api/v1/v10/final-delivery/workspace",
            "content_type": "application/json",
        },
        {
            "id": "export_zip",
            "label": "Export final package ZIP",
            "enabled": export_enabled,
            "route": "/api/v1/v10/final-delivery/export.zip",
            "content_type": "application/zip",
        },
        {
            "id": "record_delivery",
            "label": "Record delivery",
            "enabled": readiness == "ready",
            "route": None,
            "content_type": None,
        },
    ]


def _card(
    card_type: str,
    title: str,
    status: str,
    detail: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": card_type,
        "title": title,
        "status": status,
        "detail": detail,
        "data": data or {},
    }


def build_cards(readiness: str, workspace: dict[str, Any]) -> list[dict[str, Any]]:
    package_files = (
        workspace.get("package_files")
        if isinstance(workspace.get("package_files"), list)
        else []
    )
    finding_count = int(workspace.get("finding_count") or 0)
    return [
        _card(
            "delivery_readiness",
            "Delivery readiness",
            readiness,
            f"Delivery action is {workspace.get('delivery_action') or 'unknown'}.",
            {
                "delivery_action": workspace.get("delivery_action"),
                "package_ready": workspace.get("package_ready"),
            },
        ),
        _card(
            "package_inventory",
            "Package inventory",
            "ok" if package_files else "missing",
            f"Package contains {len(package_files)} manifest entries.",
            {
                "file_count": workspace.get("file_count"),
                "manifest_file_count": workspace.get("manifest_file_count"),
            },
        ),
        _card(
            "findings",
            "Findings",
            "ok" if finding_count == 0 else "review",
            f"Workspace reports {finding_count} finding(s).",
            {
                "finding_count": finding_count,
                "failure_count": workspace.get("failure_count"),
                "warning_count": workspace.get("warning_count"),
            },
        ),
        _card(
            "export_availability",
            "Export availability",
            "available" if readiness == "ready" else "blocked",
            "ZIP export is available."
            if readiness == "ready"
            else "ZIP export is blocked until readiness is resolved.",
            deepcopy(workspace.get("export") or {}),
        ),
        _card(
            "operator_next_action",
            "Operator next action",
            "actionable",
            (allowed_actions_for_readiness(readiness) or ["review_workspace"])[0],
            {"allowed_actions": allowed_actions_for_readiness(readiness)},
        ),
    ]


def build_operator_console_from_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    safe_workspace = deepcopy(workspace or {})
    readiness = readiness_for_workspace(safe_workspace)
    return {
        "schema": OPERATOR_CONSOLE_SCHEMA,
        "version": VERSION,
        "readiness": readiness,
        "delivery_action": safe_workspace.get("delivery_action"),
        "package_ready": bool(safe_workspace.get("package_ready")),
        "cards": build_cards(readiness, safe_workspace),
        "allowed_actions": allowed_actions_for_readiness(readiness),
        "blocked_actions": blocked_actions_for_readiness(readiness),
        "commands": build_commands(readiness, safe_workspace),
        "workspace": safe_workspace,
    }


def build_operator_console_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("workspace"), dict):
        workspace = safe_payload["workspace"]
    else:
        workspace = build_final_delivery_workspace_from_request(safe_payload)
    return build_operator_console_from_workspace(workspace)


def build_operator_commands_from_request(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    return list(build_operator_console_from_request(payload).get("commands") or [])
