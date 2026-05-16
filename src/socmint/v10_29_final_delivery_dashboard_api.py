from __future__ import annotations

from copy import deepcopy
from typing import Any

from .v10_28_final_delivery_capsule_export_pack import build_final_delivery_capsule_export_pack_from_request

FINAL_DELIVERY_DASHBOARD_API_SCHEMA = "socmint.v10_29.final_delivery_dashboard_api"
VERSION = "v10.29.0"


def _capsule(pack: dict[str, Any]) -> dict[str, Any]:
    return pack.get("capsule") if isinstance(pack.get("capsule"), dict) else {}


def _receipt(capsule: dict[str, Any]) -> dict[str, Any]:
    return capsule.get("operator_receipt") if isinstance(capsule.get("operator_receipt"), dict) else {}


def _summary(pack: dict[str, Any]) -> dict[str, Any]:
    return pack.get("summary") if isinstance(pack.get("summary"), dict) else {}


def _manifest(pack: dict[str, Any]) -> dict[str, Any]:
    return pack.get("manifest") if isinstance(pack.get("manifest"), dict) else {}


def build_status_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    capsule = _capsule(pack)
    receipt = _receipt(capsule)
    summary = _summary(pack)
    manifest = _manifest(pack)
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    return [
        {
            "type": "readiness",
            "title": "Final delivery readiness",
            "status": pack.get("readiness") or "unknown",
            "detail": f"Delivery readiness is {pack.get('readiness') or 'unknown'}.",
            "data": {"readiness": pack.get("readiness"), "bundle_name": pack.get("bundle_name")},
        },
        {
            "type": "evidence_capsule",
            "title": "Evidence capsule",
            "status": "available" if pack.get("capsule_id") else "missing",
            "detail": "Final delivery evidence capsule is available." if pack.get("capsule_id") else "Evidence capsule is missing.",
            "data": {"capsule_id": pack.get("capsule_id"), "card_count": summary.get("card_count")},
        },
        {
            "type": "audit_receipt",
            "title": "Audit receipt",
            "status": "available" if receipt.get("audit_id") else "missing",
            "detail": "Operator receipt is available." if receipt.get("audit_id") else "Operator receipt is missing.",
            "data": {"audit_id": receipt.get("audit_id"), "export_available": receipt.get("export_available")},
        },
        {
            "type": "package_inventory",
            "title": "Package inventory",
            "status": "ok" if manifest_files else "missing",
            "detail": f"Export pack contains {len(manifest_files)} manifest entries.",
            "data": {"file_count": pack.get("file_count"), "manifest_file_count": manifest.get("file_count")},
        },
        {
            "type": "export_pack",
            "title": "Export pack",
            "status": "available" if pack.get("pack_id") else "missing",
            "detail": "Capsule export pack is available." if pack.get("pack_id") else "Capsule export pack is missing.",
            "data": {"pack_id": pack.get("pack_id"), "required_file_count": pack.get("file_count")},
        },
    ]


def build_api_actions() -> list[dict[str, Any]]:
    return [
        {
            "id": "console",
            "label": "Get operator console",
            "route": "/api/v1/v10/final-delivery/console",
            "method": "POST",
            "content_type": "application/json",
        },
        {
            "id": "audit_trail",
            "label": "Get audit trail",
            "route": "/api/v1/v10/final-delivery/audit-trail",
            "method": "POST",
            "content_type": "application/json",
        },
        {
            "id": "evidence_capsule",
            "label": "Get evidence capsule",
            "route": "/api/v1/v10/final-delivery/evidence-capsule",
            "method": "POST",
            "content_type": "application/json",
        },
        {
            "id": "evidence_capsule_summary",
            "label": "Get evidence capsule summary",
            "route": "/api/v1/v10/final-delivery/evidence-capsule/summary",
            "method": "POST",
            "content_type": "application/json",
        },
        {
            "id": "export_pack",
            "label": "Get capsule export pack",
            "route": "/api/v1/v10/final-delivery/evidence-capsule/export",
            "method": "POST",
            "content_type": "application/json",
        },
        {
            "id": "export_zip",
            "label": "Export capsule ZIP",
            "route": "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
            "method": "POST",
            "content_type": "application/zip",
        },
    ]


def build_export_metadata(pack: dict[str, Any]) -> dict[str, Any]:
    capsule = _capsule(pack)
    receipt = _receipt(capsule)
    return {
        "available": bool(pack.get("pack_id")),
        "zip_available": bool(receipt.get("export_available")),
        "json_route": "/api/v1/v10/final-delivery/evidence-capsule/export",
        "zip_route": "/api/v1/v10/final-delivery/evidence-capsule/export.zip",
        "content_type": "application/zip",
    }


def build_final_delivery_dashboard_api_from_pack(pack: dict[str, Any]) -> dict[str, Any]:
    safe_pack = deepcopy(pack or {})
    return {
        "schema": FINAL_DELIVERY_DASHBOARD_API_SCHEMA,
        "version": VERSION,
        "readiness": safe_pack.get("readiness"),
        "bundle_name": safe_pack.get("bundle_name"),
        "capsule_id": safe_pack.get("capsule_id"),
        "pack_id": safe_pack.get("pack_id"),
        "status_cards": build_status_cards(safe_pack),
        "api_actions": build_api_actions(),
        "export": build_export_metadata(safe_pack),
        "summary": deepcopy(safe_pack.get("summary") or {}),
        "pack": safe_pack,
    }


def build_final_delivery_dashboard_api_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("pack"), dict):
        pack = safe_payload["pack"]
    else:
        pack = build_final_delivery_capsule_export_pack_from_request(safe_payload)
    return build_final_delivery_dashboard_api_from_pack(pack)


def build_final_delivery_dashboard_actions_from_request(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(build_final_delivery_dashboard_api_from_request(payload).get("api_actions") or [])
