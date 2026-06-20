from __future__ import annotations

from copy import deepcopy
from typing import Any

from .case_delivery_handoff_package_v15_1 import PACKAGE_FILES
from .case_delivery_handoff_package_v15_1 import (
    build_case_delivery_handoff_package_from_request,
)
from .case_delivery_handoff_package_v15_1 import canonical_json
from .case_delivery_handoff_package_v15_1 import sha256_text


CASE_DELIVERY_HANDOFF_VERIFICATION_SCHEMA = (
    "socmint.case_delivery_handoff_verification.v15_2"
)
VERSION = "v15.2.0"


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


def _expected_file_rows(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    workspace = (
        package.get("workspace") if isinstance(package.get("workspace"), dict) else {}
    )
    gate = package.get("gate") if isinstance(package.get("gate"), dict) else {}
    receipt = (
        package.get("operator_receipt")
        if isinstance(package.get("operator_receipt"), dict)
        else {}
    )
    contents = {
        "README.md": _readme(package),
        "case_delivery_workspace.json": canonical_json(workspace),
        "delivery_gate.json": canonical_json(gate),
        "operator_receipt.json": canonical_json(receipt),
    }
    rows = {}
    for path in PACKAGE_FILES:
        if path == "handoff_manifest.json":
            rows[path] = {
                "path": path,
                "content_type": "application/json",
                "size_bytes": 0,
                "sha256": "",
                "self_reference": True,
            }
            continue
        content = contents[path]
        rows[path] = {
            "path": path,
            "content_type": "text/markdown"
            if path.endswith(".md")
            else "application/json",
            "size_bytes": len(content.encode("utf-8")),
            "sha256": sha256_text(content),
        }
    return rows


def _manifest_rows(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = (
        package.get("manifest") if isinstance(package.get("manifest"), dict) else {}
    )
    files = (
        manifest.get("files")
        if isinstance(manifest.get("files"), list)
        else package.get("files")
    )
    rows = {}
    if not isinstance(files, list):
        return rows
    for row in files:
        if isinstance(row, dict) and row.get("path"):
            rows[str(row["path"])] = row
    return rows


def _blocker(key: str, detail: str, path: str | None = None) -> dict[str, Any]:
    return {"key": key, "detail": detail, "path": path}


def verify_case_delivery_handoff_package(package: dict[str, Any]) -> dict[str, Any]:
    safe_package = deepcopy(package or {})
    expected_rows = _expected_file_rows(safe_package)
    manifest_rows = _manifest_rows(safe_package)
    blockers = []

    missing = [path for path in PACKAGE_FILES if path not in manifest_rows]
    for path in missing:
        blockers.append(
            _blocker(
                "missing_manifest_file",
                f"{path} is missing from the handoff manifest",
                path,
            )
        )

    for path, expected in expected_rows.items():
        actual = manifest_rows.get(path)
        if not actual:
            continue
        for field in ("content_type", "size_bytes", "sha256", "self_reference"):
            if expected.get(field) != actual.get(field):
                blockers.append(
                    _blocker(
                        "manifest_mismatch",
                        f"{path} {field} expected {expected.get(field)!r} but found {actual.get(field)!r}",
                        path,
                    )
                )

    workspace = (
        safe_package.get("workspace")
        if isinstance(safe_package.get("workspace"), dict)
        else {}
    )
    gate = (
        safe_package.get("gate") if isinstance(safe_package.get("gate"), dict) else {}
    )
    workspace_gate = (
        workspace.get("gate") if isinstance(workspace.get("gate"), dict) else {}
    )
    gate_decision = gate.get("decision")
    package_decision = safe_package.get("gate_decision")
    expected_disposition = (
        "deliver" if gate_decision == "READY_FOR_DELIVERY" else "hold"
    )

    if gate != workspace_gate:
        blockers.append(
            _blocker(
                "gate_mismatch",
                "package gate does not match workspace gate",
                "delivery_gate.json",
            )
        )
    if package_decision != gate_decision:
        blockers.append(
            _blocker(
                "gate_decision_mismatch",
                "package gate decision does not match the gate",
            )
        )
    if safe_package.get("disposition") != expected_disposition:
        blockers.append(
            _blocker(
                "disposition_mismatch",
                "package disposition does not match gate decision",
            )
        )
    if safe_package.get("case_id") != workspace.get("case_id"):
        blockers.append(
            _blocker(
                "case_id_mismatch", "package case_id does not match workspace case_id"
            )
        )

    status = "verified" if not blockers else "blocked"
    return {
        "schema": CASE_DELIVERY_HANDOFF_VERIFICATION_SCHEMA,
        "version": VERSION,
        "case_id": safe_package.get("case_id"),
        "package_id": safe_package.get("package_id"),
        "status": status,
        "verified": not blockers,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "file_count": len(manifest_rows),
        "required_file_count": len(PACKAGE_FILES),
        "gate_decision": gate_decision,
        "disposition": safe_package.get("disposition"),
    }


def verify_case_delivery_handoff_package_from_request(
    case_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    package = (
        safe_payload.get("package")
        if isinstance(safe_payload.get("package"), dict)
        else None
    )
    if package is None:
        package = build_case_delivery_handoff_package_from_request(
            case_id, safe_payload
        )
    return verify_case_delivery_handoff_package(package)
