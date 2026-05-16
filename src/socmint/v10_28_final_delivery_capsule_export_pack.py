from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from typing import Any

from .v10_27_final_delivery_evidence_capsule import build_final_delivery_evidence_capsule_from_request

FINAL_DELIVERY_CAPSULE_EXPORT_PACK_SCHEMA = "socmint.v10_28.final_delivery_capsule_export_pack"
FINAL_DELIVERY_CAPSULE_EXPORT_MANIFEST_SCHEMA = "socmint.v10_28.final_delivery_capsule_export_manifest"
VERSION = "v10.28.0"

REQUIRED_FILES = (
    "README.md",
    "final_delivery_evidence_capsule.json",
    "final_delivery_evidence_capsule_summary.json",
    "operator_receipt.json",
    "manifest.json",
)
CONTENT_TYPES = {
    "README.md": "text/markdown",
    "final_delivery_evidence_capsule.json": "application/json",
    "final_delivery_evidence_capsule_summary.json": "application/json",
    "operator_receipt.json": "application/json",
    "manifest.json": "application/json",
}


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _readme(pack: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SOCMINT v10.28 Final Delivery Capsule Export Pack",
            "",
            f"Pack ID: {pack.get('pack_id') or ''}",
            f"Capsule ID: {pack.get('capsule_id') or ''}",
            f"Readiness: {pack.get('readiness') or ''}",
            f"Bundle name: {pack.get('bundle_name') or ''}",
            f"Files included: {len(REQUIRED_FILES)}",
            "",
            "## Included Files",
            "",
            *[f"- `{path}`" for path in REQUIRED_FILES],
            "",
        ]
    )


def _pack_core(capsule: dict[str, Any]) -> dict[str, Any]:
    summary = capsule.get("summary") if isinstance(capsule.get("summary"), dict) else {}
    receipt = capsule.get("operator_receipt") if isinstance(capsule.get("operator_receipt"), dict) else {}
    return {
        "schema": FINAL_DELIVERY_CAPSULE_EXPORT_PACK_SCHEMA,
        "version": VERSION,
        "capsule_id": capsule.get("capsule_id"),
        "readiness": capsule.get("readiness"),
        "bundle_name": capsule.get("bundle_name"),
        "summary": deepcopy(summary),
        "receipt": deepcopy(receipt),
    }


def _payload_files(pack: dict[str, Any]) -> dict[str, bytes]:
    capsule = deepcopy(pack.get("capsule") or {})
    summary = deepcopy(pack.get("summary") or {})
    receipt = deepcopy(capsule.get("operator_receipt") or {})
    return {
        "README.md": _readme(pack).encode("utf-8"),
        "final_delivery_evidence_capsule.json": canonical_json(capsule).encode("utf-8"),
        "final_delivery_evidence_capsule_summary.json": canonical_json(summary).encode("utf-8"),
        "operator_receipt.json": canonical_json(receipt).encode("utf-8"),
    }


def _manifest(files: dict[str, bytes]) -> dict[str, Any]:
    rows = []
    for path in REQUIRED_FILES:
        if path == "manifest.json":
            rows.append(
                {
                    "path": path,
                    "content_type": CONTENT_TYPES[path],
                    "size_bytes": 0,
                    "sha256": "",
                    "self_reference": True,
                }
            )
            continue
        data = files.get(path, b"")
        rows.append(
            {
                "path": path,
                "content_type": CONTENT_TYPES[path],
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    return {
        "schema": FINAL_DELIVERY_CAPSULE_EXPORT_MANIFEST_SCHEMA,
        "version": VERSION,
        "file_count": len(REQUIRED_FILES),
        "files": rows,
    }


def build_final_delivery_capsule_export_pack(capsule: dict[str, Any]) -> dict[str, Any]:
    safe_capsule = deepcopy(capsule or {})
    pack_id = sha256_text(canonical_json(_pack_core(safe_capsule)))
    pack: dict[str, Any] = {
        "schema": FINAL_DELIVERY_CAPSULE_EXPORT_PACK_SCHEMA,
        "version": VERSION,
        "pack_id": pack_id,
        "capsule_id": safe_capsule.get("capsule_id"),
        "readiness": safe_capsule.get("readiness"),
        "bundle_name": safe_capsule.get("bundle_name"),
        "file_count": len(REQUIRED_FILES),
        "files": [],
        "manifest": {},
        "capsule": safe_capsule,
        "summary": deepcopy(safe_capsule.get("summary") or {}),
    }
    files = _payload_files(pack)
    manifest = _manifest(files)
    pack["manifest"] = manifest
    pack["files"] = deepcopy(manifest["files"])
    return pack


def build_final_delivery_capsule_export_pack_from_request(payload: dict[str, Any]) -> dict[str, Any]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("capsule"), dict):
        capsule = safe_payload["capsule"]
    else:
        capsule = build_final_delivery_evidence_capsule_from_request(safe_payload)
    return build_final_delivery_capsule_export_pack(capsule)


def build_final_delivery_capsule_export_pack_files(pack: dict[str, Any]) -> dict[str, bytes]:
    safe_pack = deepcopy(pack or {})
    files = _payload_files(safe_pack)
    files["manifest.json"] = canonical_json(safe_pack.get("manifest") or {}).encode("utf-8")
    return {path: files[path] for path in REQUIRED_FILES}


def build_final_delivery_capsule_export_zip(pack: dict[str, Any]) -> bytes:
    files = build_final_delivery_capsule_export_pack_files(pack)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in REQUIRED_FILES:
            info = zipfile.ZipInfo(path)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_final_delivery_capsule_export_zip_from_request(payload: dict[str, Any]) -> bytes:
    return build_final_delivery_capsule_export_zip(build_final_delivery_capsule_export_pack_from_request(payload))
