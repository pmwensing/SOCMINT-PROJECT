from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .v10_25_final_delivery_operator_console import build_operator_console_from_request

FINAL_DELIVERY_AUDIT_TRAIL_SCHEMA = "socmint.v10_26.final_delivery_audit_trail"
VERSION = "v10.26.0"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _export_available(console: dict[str, Any]) -> bool:
    commands = console.get("commands") if isinstance(console.get("commands"), list) else []
    for command in commands:
        if isinstance(command, dict) and command.get("id") == "export_zip":
            return bool(command.get("enabled"))
    return False


def _workspace(console: dict[str, Any]) -> dict[str, Any]:
    return console.get("workspace") if isinstance(console.get("workspace"), dict) else {}


def _core_audit_fields(console: dict[str, Any]) -> dict[str, Any]:
    safe_console = deepcopy(console or {})
    workspace = _workspace(safe_console)
    return {
        "schema": FINAL_DELIVERY_AUDIT_TRAIL_SCHEMA,
        "version": VERSION,
        "readiness": safe_console.get("readiness"),
        "delivery_action": safe_console.get("delivery_action"),
        "package_ready": bool(safe_console.get("package_ready")),
        "bundle_name": workspace.get("bundle_name"),
        "file_count": int(workspace.get("file_count") or 0),
        "finding_count": int(workspace.get("finding_count") or 0),
        "allowed_actions": list(safe_console.get("allowed_actions") or []),
        "blocked_actions": list(safe_console.get("blocked_actions") or []),
        "command_count": len(safe_console.get("commands") or []),
        "export_available": _export_available(safe_console),
    }


def build_operator_receipt(audit_fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": audit_fields.get("audit_id"),
        "version": VERSION,
        "readiness": audit_fields.get("readiness"),
        "delivery_action": audit_fields.get("delivery_action"),
        "package_ready": bool(audit_fields.get("package_ready")),
        "bundle_name": audit_fields.get("bundle_name"),
        "file_count": int(audit_fields.get("file_count") or 0),
        "finding_count": int(audit_fields.get("finding_count") or 0),
        "export_available": bool(audit_fields.get("export_available")),
        "command_count": int(audit_fields.get("command_count") or 0),
    }


def build_final_delivery_audit_trail_from_console(console: dict[str, Any]) -> dict[str, Any]:
    safe_console = deepcopy(console or {})
    core = _core_audit_fields(safe_console)
    audit_id = sha256_text(canonical_json(core))
    audit = {
        **core,
        "generated_at": utc_now(),
        "audit_id": audit_id,
        "operator_receipt": {},
        "console": safe_console,
    }
    audit["operator_receipt"] = build_operator_receipt(audit)
    return audit


def build_final_delivery_audit_trail_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("console"), dict):
        console = safe_payload["console"]
    else:
        console = build_operator_console_from_request(safe_payload)
    return build_final_delivery_audit_trail_from_console(console)


def build_final_delivery_audit_receipt_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(build_final_delivery_audit_trail_from_request(payload).get("operator_receipt") or {})
