from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_master_delivery_index_v7_5_13 import build_master_delivery_index
from .dossier_finalization_master_delivery_index_v7_5_13 import render_master_delivery_index_markdown

MASTER_DELIVERY_EXPORT_BUNDLE_SCHEMA = "socmint.v7_5_14.dossier_finalization_master_delivery_export_bundle"
MASTER_DELIVERY_EXPORT_MANIFEST_SCHEMA = "socmint.v7_5_14.dossier_finalization_master_delivery_export_manifest"
APPROVED_LINE = "v7.5.14"

REQUIRED_FILES = (
    "README.md",
    "master_delivery_index.json",
    "master_delivery_index.md",
    "master_delivery_index_summary.json",
    "manifest.json",
)
CONTENT_TYPES = {
    "README.md": "text/markdown",
    "master_delivery_index.json": "application/json",
    "master_delivery_index.md": "text/markdown",
    "master_delivery_index_summary.json": "application/json",
    "manifest.json": "application/json",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def safe_bundle_name(name: str | None) -> str:
    raw = (name or "master-delivery-package").strip().lower()
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", raw).strip(".-_")
    return cleaned or "master-delivery-package"


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _readme(bundle: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SOCMINT v7.5.14 Master Delivery Package Export Bundle",
            "",
            f"Bundle name: {bundle.get('bundle_name')}",
            f"Delivery action: {bundle.get('delivery_action')}",
            f"Verification status: {bundle.get('verification_status')}",
            f"Files included: {len(REQUIRED_FILES)}",
            "",
            "## Included Files",
            "",
            *[f"- `{path}`" for path in REQUIRED_FILES],
            "",
        ]
    )


def _base_payload_files(bundle: dict[str, Any]) -> dict[str, bytes]:
    index = deepcopy(bundle.get("index") or {})
    summary = deepcopy(bundle.get("summary") or {})
    return {
        "README.md": _readme(bundle).encode("utf-8"),
        "master_delivery_index.json": canonical_json(index).encode("utf-8"),
        "master_delivery_index.md": render_master_delivery_index_markdown(index).encode("utf-8"),
        "master_delivery_index_summary.json": canonical_json(summary).encode("utf-8"),
    }


def _manifest(files: dict[str, bytes], *, generated_at: str | None = None) -> dict[str, Any]:
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
        "schema": MASTER_DELIVERY_EXPORT_MANIFEST_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": generated_at or utc_now(),
        "file_count": len(REQUIRED_FILES),
        "files": rows,
    }


def build_master_delivery_export_bundle(index: dict[str, Any], *, bundle_name: str | None = None) -> dict[str, Any]:
    safe_index = deepcopy(index or {})
    bundle = {
        "schema": MASTER_DELIVERY_EXPORT_BUNDLE_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "bundle_name": safe_bundle_name(bundle_name),
        "delivery_action": safe_index.get("delivery_action"),
        "verification_status": safe_index.get("verification_status"),
        "file_count": len(REQUIRED_FILES),
        "files": [],
        "manifest": {},
        "summary": deepcopy(safe_index.get("summary") or {}),
        "index": safe_index,
    }
    files = _base_payload_files(bundle)
    manifest = _manifest(files, generated_at=bundle["generated_at"])
    bundle["manifest"] = manifest
    bundle["files"] = deepcopy(manifest["files"])
    return bundle


def build_master_delivery_export_bundle_files(bundle: dict[str, Any]) -> dict[str, bytes]:
    safe_bundle = deepcopy(bundle or {})
    files = _base_payload_files(safe_bundle)
    manifest = deepcopy(safe_bundle.get("manifest") or {})
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return {path: files[path] for path in REQUIRED_FILES}


def build_master_delivery_export_zip(bundle: dict[str, Any]) -> bytes:
    files = build_master_delivery_export_bundle_files(bundle)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in REQUIRED_FILES:
            info = zipfile.ZipInfo(path)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_master_delivery_export_bundle_from_verification_report(
    verification_report: dict[str, Any],
    *,
    operator: str | None = None,
    notes: str | None = None,
    bundle_name: str | None = None,
) -> dict[str, Any]:
    index = build_master_delivery_index(deepcopy(verification_report or {}), operator=operator, notes=notes)
    return build_master_delivery_export_bundle(index, bundle_name=bundle_name)
