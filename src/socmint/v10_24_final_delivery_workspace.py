from __future__ import annotations

from copy import deepcopy
from typing import Any

from .dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_bundle
from .dossier_finalization_master_delivery_export_bundle_v7_5_14 import build_master_delivery_export_zip

FINAL_DELIVERY_WORKSPACE_SCHEMA = "socmint.v10_24.final_delivery_workspace"
VERSION = "v10.24.0"

DELIVER_ACTIONS = ["review_final_package", "export_zip", "record_delivery"]
REVIEW_ACTIONS = ["review_findings", "resolve_or_acknowledge", "regenerate_if_needed"]
REGENERATE_ACTIONS = ["regenerate_v7_5_14_package", "rerun_verification"]


def operator_actions_for_delivery(delivery_action: str | None) -> list[str]:
    if delivery_action == "deliver_ready":
        return list(DELIVER_ACTIONS)
    if delivery_action == "human_review_required":
        return list(REVIEW_ACTIONS)
    return list(REGENERATE_ACTIONS)


def package_ready(bundle: dict[str, Any]) -> bool:
    return bundle.get("delivery_action") == "deliver_ready" and int(bundle.get("file_count") or 0) > 0


def build_final_delivery_workspace_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    safe_bundle = deepcopy(bundle or {})
    manifest = safe_bundle.get("manifest") if isinstance(safe_bundle.get("manifest"), dict) else {}
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    index = safe_bundle.get("index") if isinstance(safe_bundle.get("index"), dict) else {}
    findings = index.get("findings") if isinstance(index.get("findings"), list) else []
    failure_count = int(index.get("failure_count") or 0)
    warning_count = int(index.get("warning_count") or 0)
    delivery_action = safe_bundle.get("delivery_action")
    return {
        "schema": FINAL_DELIVERY_WORKSPACE_SCHEMA,
        "version": VERSION,
        "delivery_action": delivery_action,
        "verification_status": safe_bundle.get("verification_status"),
        "package_ready": package_ready(safe_bundle),
        "bundle_name": safe_bundle.get("bundle_name"),
        "file_count": int(safe_bundle.get("file_count") or 0),
        "manifest_file_count": int(manifest.get("file_count") or len(manifest_files)),
        "finding_count": len(findings),
        "failure_count": failure_count,
        "warning_count": warning_count,
        "package_files": [deepcopy(row) for row in manifest_files],
        "operator_actions": operator_actions_for_delivery(delivery_action),
        "export": {
            "available": True,
            "format": "zip",
            "content_type": "application/zip",
        },
    }


def build_final_delivery_workspace_from_index(index: dict[str, Any], *, bundle_name: str | None = None) -> dict[str, Any]:
    bundle = build_master_delivery_export_bundle(deepcopy(index or {}), bundle_name=bundle_name)
    return build_final_delivery_workspace_from_bundle(bundle)


def build_final_delivery_bundle_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("bundle"), dict):
        return safe_payload["bundle"]
    index = safe_payload.get("index") if isinstance(safe_payload.get("index"), dict) else safe_payload
    return build_master_delivery_export_bundle(index, bundle_name=safe_payload.get("bundle_name"))


def build_final_delivery_workspace_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    return build_final_delivery_workspace_from_bundle(build_final_delivery_bundle_from_request(payload))


def build_final_delivery_export_zip_from_request(payload: dict[str, Any]) -> bytes:
    return build_master_delivery_export_zip(build_final_delivery_bundle_from_request(payload))
