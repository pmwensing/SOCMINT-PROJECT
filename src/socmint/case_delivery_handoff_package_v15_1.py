from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .case_delivery_workspace_v15 import build_case_delivery_workspace


CASE_DELIVERY_HANDOFF_PACKAGE_SCHEMA = "socmint.case_delivery_handoff_package.v15_1"
CASE_DELIVERY_HANDOFF_MANIFEST_SCHEMA = (
    "socmint.case_delivery_handoff_package.v15_1.manifest"
)
VERSION = "v15.1.0"

PACKAGE_FILES = (
    "README.md",
    "case_delivery_workspace.json",
    "delivery_gate.json",
    "handoff_manifest.json",
    "operator_receipt.json",
)


def canonical_json(data: dict[str, Any]) -> str:
    return (
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _latest_delivery_id(workspace: dict[str, Any]) -> str | None:
    latest = (
        workspace.get("latest_delivery")
        if isinstance(workspace.get("latest_delivery"), dict)
        else {}
    )
    registry = (
        workspace.get("delivery_registry")
        if isinstance(workspace.get("delivery_registry"), dict)
        else {}
    )
    return latest.get("delivery_id") or registry.get("latest_delivery_id")


def _operator_receipt(
    workspace: dict[str, Any], operator: str | None, notes: str | None
) -> dict[str, Any]:
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    return {
        "case_id": workspace.get("case_id"),
        "delivery_id": _latest_delivery_id(workspace),
        "operator": operator or "unassigned",
        "notes": notes or "",
        "gate_decision": gate.get("decision"),
        "accepted_for_delivery": gate.get("decision") == "READY_FOR_DELIVERY",
        "blocker_count": gate.get("blocker_count", 0),
    }


def _remediation_actions(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    blockers = gate.get("blockers") if isinstance(gate.get("blockers"), list) else []
    actions = []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        actions.append(
            {
                "key": blocker.get("key"),
                "label": blocker.get("label"),
                "detail": blocker.get("detail"),
                "href": blocker.get("href"),
                "action": blocker.get("key"),
            }
        )
    return actions


def _readme(package: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SOCMINT v15.1 Case Delivery Handoff Package",
            "",
            f"Case ID: {package.get('case_id') or ''}",
            f"Delivery ID: {package.get('delivery_id') or 'none'}",
            f"Disposition: {package.get('disposition') or ''}",
            f"Gate decision: {package.get('gate_decision') or ''}",
            f"Operator: {package.get('operator_receipt', {}).get('operator') or 'unassigned'}",
            "",
            "## Included Files",
            "",
            *[f"- `{path}`" for path in PACKAGE_FILES],
            "",
        ]
    )


def _manifest(
    package: dict[str, Any], workspace: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    files = {
        "README.md": _readme(package),
        "case_delivery_workspace.json": canonical_json(workspace),
        "delivery_gate.json": canonical_json(gate),
        "operator_receipt.json": canonical_json(receipt),
    }
    rows = []
    for path in PACKAGE_FILES:
        if path == "handoff_manifest.json":
            rows.append(
                {
                    "path": path,
                    "content_type": "application/json",
                    "size_bytes": 0,
                    "sha256": "",
                    "self_reference": True,
                }
            )
            continue
        content = files[path]
        rows.append(
            {
                "path": path,
                "content_type": "text/markdown"
                if path.endswith(".md")
                else "application/json",
                "size_bytes": len(content.encode("utf-8")),
                "sha256": sha256_text(content),
            }
        )
    return {
        "schema": CASE_DELIVERY_HANDOFF_MANIFEST_SCHEMA,
        "version": VERSION,
        "file_count": len(PACKAGE_FILES),
        "files": rows,
    }


def build_case_delivery_handoff_package(
    case_id: str,
    payload: dict[str, Any] | None = None,
    *,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    workspace_payload = deepcopy(payload or {})
    workspace_payload["_skip_delivery_pipeline"] = True
    workspace = build_case_delivery_workspace(case_id, workspace_payload)
    gate = workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    disposition = "deliver" if gate.get("decision") == "READY_FOR_DELIVERY" else "hold"
    receipt = _operator_receipt(workspace, operator, notes)
    package_core = {
        "schema": CASE_DELIVERY_HANDOFF_PACKAGE_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "delivery_id": _latest_delivery_id(workspace),
        "disposition": disposition,
        "gate_decision": gate.get("decision"),
        "blocker_count": gate.get("blocker_count", 0),
        "operator_receipt": receipt,
    }
    package_id = sha256_text(canonical_json(package_core))
    package = {
        **package_core,
        "package_id": package_id,
        "workspace": workspace,
        "gate": deepcopy(gate),
        "manifest": {},
        "files": [],
        "remediation_actions": _remediation_actions(workspace),
        "delivery_links": [
            {"label": "Workspace API", "href": f"/api/v1/case-delivery/{case_id}"},
            {
                "label": "Handoff package",
                "href": f"/api/v1/case-delivery/{case_id}/handoff-package",
            },
        ],
    }
    manifest = _manifest(package, workspace, receipt)
    package["manifest"] = manifest
    package["files"] = deepcopy(manifest["files"])
    return package


def build_case_delivery_handoff_package_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    operator = (
        safe_payload.get("operator")
        if isinstance(safe_payload.get("operator"), str)
        else None
    )
    notes = (
        safe_payload.get("notes")
        if isinstance(safe_payload.get("notes"), str)
        else None
    )
    return build_case_delivery_handoff_package(
        case_id, safe_payload, operator=operator, notes=notes
    )


def case_delivery_handoff_markdown(package: dict[str, Any]) -> str:
    lines = [
        f"# Case Delivery Handoff - {package.get('case_id')}",
        "",
        f"Disposition: {package.get('disposition')}",
        f"Gate decision: {package.get('gate_decision')}",
        f"Delivery ID: {package.get('delivery_id') or 'none'}",
        f"Package ID: {package.get('package_id')}",
        "",
        "| File | SHA-256 |",
        "|---|---|",
    ]
    for row in package.get("files", []):
        if isinstance(row, dict):
            lines.append(f"| {row.get('path')} | {row.get('sha256') or 'self'} |")
    actions = (
        package.get("remediation_actions")
        if isinstance(package.get("remediation_actions"), list)
        else []
    )
    if actions:
        lines.extend(["", "## Remediation Actions", ""])
        for action in actions:
            if isinstance(action, dict):
                lines.append(f"- {action.get('label')}: {action.get('detail')}")
    return "\n".join(lines) + "\n"
