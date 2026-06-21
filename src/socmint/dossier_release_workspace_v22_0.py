from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any

from .dossier_final_export_package_v21_6 import _latest_export

SCHEMA = "socmint.dossier_release_workspace.v22_0"
VERSION = "v22.0.0"
DEFAULT_CHANNELS = ("secure_portal", "encrypted_email", "managed_download")


def _recipient_catalog(
    explicit: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if explicit is not None:
        values = explicit
    else:
        try:
            values = json.loads(os.environ.get("SOCMINT_AUTHORIZED_RECIPIENTS", "[]"))
        except json.JSONDecodeError:
            values = []
    catalog = []
    for value in values if isinstance(values, list) else []:
        if not isinstance(value, dict) or not value.get("recipient_id"):
            continue
        channels = [
            channel
            for channel in value.get("allowed_channels", DEFAULT_CHANNELS)
            if channel in DEFAULT_CHANNELS
        ]
        catalog.append(
            {
                "recipient_id": str(value["recipient_id"]),
                "display_name": str(value.get("display_name") or value["recipient_id"]),
                "organization": str(value.get("organization") or ""),
                "role": str(value.get("role") or "recipient"),
                "authorized": value.get("authorized", True) is True,
                "allowed_channels": channels,
            }
        )
    return sorted(
        catalog, key=lambda item: (item["display_name"], item["recipient_id"])
    )


def build_dossier_release_workspace(
    case_id: str,
    *,
    selected_recipient_id: str | None = None,
    selected_channel: str | None = None,
    recipients: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    export_package = _latest_export(case_id)
    catalog = _recipient_catalog(recipients)
    selected = next(
        (item for item in catalog if item["recipient_id"] == selected_recipient_id),
        None,
    )
    blockers: list[dict[str, Any]] = []

    if export_package is None:
        blockers.append({"key": "generated_v21_export_required"})
    else:
        approval = export_package.get("approval_record") or {}
        integrity = export_package.get("integrity") or {}
        if not approval.get("approval_id") or not approval.get("approval_record_id"):
            blockers.append({"key": "export_approval_record_missing"})
        required_hashes = {
            "content_sha256",
            "dossier_sha256",
            "citation_catalog_sha256",
            "source_manifest_sha256",
            "approval_record_sha256",
            "quality_review_sha256",
        }
        missing_hashes = sorted(required_hashes - set(integrity))
        if missing_hashes:
            blockers.append(
                {"key": "export_integrity_incomplete", "missing": missing_hashes}
            )
        if not export_package.get("export_package_id") or not export_package.get(
            "export_package_sha256"
        ):
            blockers.append({"key": "export_package_identity_missing"})

    if not catalog:
        blockers.append({"key": "authorized_recipient_catalog_empty"})
    if selected_recipient_id and selected is None:
        blockers.append({"key": "selected_recipient_not_authorized"})
    if selected is not None and not selected["authorized"]:
        blockers.append({"key": "selected_recipient_inactive"})
    if selected_channel and selected is None:
        blockers.append({"key": "recipient_required_for_channel_selection"})
    if selected is not None and not selected_channel:
        blockers.append({"key": "delivery_channel_required"})
    if selected is not None and selected_channel not in selected["allowed_channels"]:
        blockers.append({"key": "delivery_channel_not_authorized"})

    package_ready = export_package is not None and not any(
        blocker["key"].startswith("export_")
        or blocker["key"] == "generated_v21_export_required"
        for blocker in blockers
    )
    selection_ready = bool(selected and selected_channel) and not any(
        blocker["key"].startswith("selected_")
        or blocker["key"].startswith("delivery_")
        or blocker["key"] == "recipient_required_for_channel_selection"
        for blocker in blockers
    )
    release_ready = package_ready and selection_ready
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "ready_for_delivery_workspace"
        if release_ready
        else "needs_configuration",
        "release_ready": release_ready,
        "transmission_performed": False,
        "export_package": deepcopy(export_package),
        "approval_state": deepcopy((export_package or {}).get("approval_record") or {}),
        "integrity_state": deepcopy((export_package or {}).get("integrity") or {}),
        "recipient_catalog": catalog,
        "selected_recipient": deepcopy(selected),
        "available_channels": list(
            selected["allowed_channels"] if selected else DEFAULT_CHANNELS
        ),
        "selected_channel": selected_channel,
        "package_ready": package_ready,
        "selection_ready": selection_ready,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "case_delivery_workspace": {
            "href": f"/case-delivery?case_id={case_id}",
            "api_href": f"/api/v1/case-delivery/{case_id}",
            "handoff_context": {
                "export_package_id": (export_package or {}).get("export_package_id"),
                "export_package_sha256": (export_package or {}).get(
                    "export_package_sha256"
                ),
                "recipient_id": selected_recipient_id,
                "delivery_channel": selected_channel,
            },
        },
        "next_action": (
            "open_case_delivery_workspace"
            if release_ready
            else blockers[0]["key"]
            if blockers
            else "select_release_configuration"
        ),
    }
