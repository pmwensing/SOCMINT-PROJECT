from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from .v10_26_final_delivery_audit_trail import build_final_delivery_audit_trail_from_request

FINAL_DELIVERY_EVIDENCE_CAPSULE_SCHEMA = "socmint.v10_27.final_delivery_evidence_capsule"
FINAL_DELIVERY_EVIDENCE_CAPSULE_SUMMARY_SCHEMA = "socmint.v10_27.final_delivery_evidence_capsule.summary"
VERSION = "v10.27.0"


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _console(audit_trail: dict[str, Any]) -> dict[str, Any]:
    return audit_trail.get("console") if isinstance(audit_trail.get("console"), dict) else {}


def _workspace(console: dict[str, Any]) -> dict[str, Any]:
    return console.get("workspace") if isinstance(console.get("workspace"), dict) else {}


def _package_file_paths(workspace: dict[str, Any]) -> list[str]:
    rows = workspace.get("package_files") if isinstance(workspace.get("package_files"), list) else []
    return sorted(str(row.get("path")) for row in rows if isinstance(row, dict) and row.get("path"))


def summarize_evidence_capsule(capsule: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": FINAL_DELIVERY_EVIDENCE_CAPSULE_SUMMARY_SCHEMA,
        "version": VERSION,
        "capsule_id": capsule.get("capsule_id"),
        "readiness": capsule.get("readiness"),
        "bundle_name": capsule.get("bundle_name"),
        "package_file_count": len(capsule.get("package_files") or []),
        "card_count": len(capsule.get("cards") or []),
        "command_count": len(capsule.get("commands") or []),
        "audit_id": (capsule.get("audit_trail") or {}).get("audit_id") if isinstance(capsule.get("audit_trail"), dict) else None,
        "export_available": bool((capsule.get("operator_receipt") or {}).get("export_available"))
        if isinstance(capsule.get("operator_receipt"), dict)
        else False,
    }


def _capsule_core(audit_trail: dict[str, Any]) -> dict[str, Any]:
    console = _console(audit_trail)
    workspace = _workspace(console)
    receipt = audit_trail.get("operator_receipt") if isinstance(audit_trail.get("operator_receipt"), dict) else {}
    return {
        "schema": FINAL_DELIVERY_EVIDENCE_CAPSULE_SCHEMA,
        "version": VERSION,
        "readiness": audit_trail.get("readiness"),
        "bundle_name": audit_trail.get("bundle_name"),
        "package_file_paths": _package_file_paths(workspace),
        "card_types": [str(card.get("type")) for card in console.get("cards") or [] if isinstance(card, dict) and card.get("type")],
        "command_ids": [str(command.get("id")) for command in console.get("commands") or [] if isinstance(command, dict) and command.get("id")],
        "export_available": bool(receipt.get("export_available")),
        "finding_count": int(receipt.get("finding_count") or 0),
        "file_count": int(receipt.get("file_count") or 0),
    }


def build_final_delivery_evidence_capsule_from_audit_trail(audit_trail: dict[str, Any]) -> dict[str, Any]:
    safe_audit = deepcopy(audit_trail or {})
    console = _console(safe_audit)
    workspace = _workspace(console)
    core = _capsule_core(safe_audit)
    capsule_id = sha256_text(canonical_json(core))
    capsule: dict[str, Any] = {
        "schema": FINAL_DELIVERY_EVIDENCE_CAPSULE_SCHEMA,
        "version": VERSION,
        "capsule_id": capsule_id,
        "readiness": safe_audit.get("readiness"),
        "bundle_name": safe_audit.get("bundle_name"),
        "package_files": deepcopy(workspace.get("package_files") or []),
        "cards": deepcopy(console.get("cards") or []),
        "commands": deepcopy(console.get("commands") or []),
        "operator_receipt": deepcopy(safe_audit.get("operator_receipt") or {}),
        "audit_trail": safe_audit,
        "workspace": deepcopy(workspace),
        "console": deepcopy(console),
        "summary": {},
    }
    capsule["summary"] = summarize_evidence_capsule(capsule)
    return capsule


def build_final_delivery_evidence_capsule_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("audit_trail"), dict):
        audit_trail = safe_payload["audit_trail"]
    else:
        audit_trail = build_final_delivery_audit_trail_from_request(safe_payload)
    return build_final_delivery_evidence_capsule_from_audit_trail(audit_trail)


def build_final_delivery_evidence_capsule_summary_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(build_final_delivery_evidence_capsule_from_request(payload).get("summary") or {})
