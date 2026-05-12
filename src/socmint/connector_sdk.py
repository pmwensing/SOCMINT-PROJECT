from __future__ import annotations

import hashlib
import json
from typing import Any

from .connectors import CONNECTORS
from .connectors import ConnectorSpec
from .connectors import list_connectors
from .connectors import render_command

SDK_SCHEMA = "socmint.connector_sdk.v8_7_0"

REQUIRED_SPEC_KEYS = {"name", "target_types", "command"}
ALLOWED_TARGET_TYPES = {"email", "phone", "username", "name", "domain", "url", "target"}


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def spec_to_manifest(name: str, spec: ConnectorSpec) -> dict[str, Any]:
    payload = {
        "name": spec.name,
        "target_types": list(spec.target_types),
        "command": list(spec.command),
        "timeout": int(spec.timeout),
        "capability_tags": list(spec.target_types),
        "install_status": "registered",
        "sdk_version": SDK_SCHEMA,
    }
    payload["manifest_sha256"] = _stable_hash(payload)
    return payload


def validate_connector_spec(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED_SPEC_KEYS - set(manifest))
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    name = str(manifest.get("name") or "").strip()
    if not name:
        errors.append("Connector name is required.")
    target_types = manifest.get("target_types") or []
    if not isinstance(target_types, list | tuple) or not target_types:
        errors.append("target_types must be a non-empty list.")
    else:
        unknown = sorted(set(target_types) - ALLOWED_TARGET_TYPES)
        if unknown:
            warnings.append(f"Unknown target types: {', '.join(unknown)}")
    command = manifest.get("command") or []
    if not isinstance(command, list | tuple) or not command:
        errors.append("command must be a non-empty list.")
    elif not any("{" in str(part) and "}" in str(part) for part in command):
        warnings.append("command does not include a target placeholder.")
    timeout = int(manifest.get("timeout") or 300)
    if timeout < 10:
        warnings.append("timeout is very low.")
    if timeout > 900:
        warnings.append("timeout is high; consider an async job timeout.")
    return {
        "schema": SDK_SCHEMA,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "manifest_sha256": _stable_hash(manifest),
    }


def registered_connector_manifests() -> dict[str, Any]:
    manifests = [spec_to_manifest(name, spec) for name, spec in sorted(CONNECTORS.items())]
    return {
        "schema": SDK_SCHEMA,
        "connectors": manifests,
        "count": len(manifests),
        "catalog_sha256": _stable_hash(manifests),
    }


def sdk_fixture_run(name: str, target: str, target_type: str) -> dict[str, Any]:
    if name not in CONNECTORS:
        return {"schema": SDK_SCHEMA, "valid": False, "errors": ["Unknown connector."]}
    spec = CONNECTORS[name]
    manifest = spec_to_manifest(name, spec)
    validation = validate_connector_spec(manifest)
    if target_type not in spec.target_types:
        validation["valid"] = False
        validation["errors"].append(f"Unsupported target type: {target_type}")
        return validation
    command = render_command(spec, target, target_type)
    return {
        "schema": SDK_SCHEMA,
        "valid": validation["valid"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "connector": name,
        "target": target,
        "target_type": target_type,
        "rendered_command": command,
        "dry_run_safe": True,
        "manifest_sha256": manifest["manifest_sha256"],
    }


def connector_marketplace_sdk_payload() -> dict[str, Any]:
    catalog = registered_connector_manifests()
    raw = list_connectors()
    return {
        "schema": SDK_SCHEMA,
        "catalog": catalog,
        "marketplace": [
            {
                **item,
                "sdk_validation": validate_connector_spec(item),
                "listing_state": "publishable" if validate_connector_spec(item)["valid"] else "needs_repair",
            }
            for item in raw
        ],
    }
