from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_certificate_handoff_index_v7_5_7 import build_handoff_index
from .dossier_finalization_certificate_handoff_index_v7_5_7 import (
    render_handoff_index_markdown,
)
from .dossier_finalization_certificate_handoff_index_v7_5_7 import (
    summarize_handoff_index,
)

HANDOFF_EXPORT_BUNDLE_SCHEMA = (
    "socmint.v7_5_8.dossier_finalization_handoff_export_bundle"
)
HANDOFF_EXPORT_MANIFEST_SCHEMA = (
    "socmint.v7_5_8.dossier_finalization_handoff_export_manifest"
)
APPROVED_LINE = "v7.5.8"
DEFAULT_BUNDLE_NAME = "socmint-v7.5.8-handoff-index-export"
REQUIRED_FILES = (
    "README.md",
    "handoff_index.json",
    "handoff_index.md",
    "handoff_index_summary.json",
    "manifest.json",
)
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_handoff_bundle_name(value: str | None) -> str:
    raw = (value or DEFAULT_BUNDLE_NAME).strip().lower()
    cleaned = re.sub(r"[^a-z0-9_.-]+", "-", raw)
    cleaned = re.sub(r"-+", "-", cleaned).strip(".-_")
    return cleaned or DEFAULT_BUNDLE_NAME


def _content_type(path: str) -> str:
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".md"):
        return "text/markdown"
    if path.endswith(".txt"):
        return "text/plain"
    return "application/octet-stream"


def _readme(bundle: dict[str, Any]) -> str:
    index = bundle.get("index") or {}
    return "\n".join(
        [
            "# SOCMINT v7.5.8 Handoff Index Export Bundle",
            "",
            f"Bundle: `{bundle.get('bundle_name')}`",
            f"Recommended action: `{bundle.get('recommended_action')}`",
            f"Verification status: `{bundle.get('verification_status')}`",
            f"Certificate status: `{bundle.get('certificate_status')}`",
            f"Generated at: `{bundle.get('generated_at')}`",
            "",
            "## Contents",
            "",
            "- `handoff_index.json` — full v7.5.7 handoff index JSON.",
            "- `handoff_index.md` — operator-readable handoff index Markdown.",
            "- `handoff_index_summary.json` — compact handoff index summary.",
            "- `manifest.json` — bundle file list with SHA-256 hashes and sizes.",
            "- `README.md` — this operator handoff note.",
            "",
            "## Guardrails",
            "",
            "This bundle is generated in memory. It does not execute connectors, collect data, write to the database, or persist artifacts by itself.",
            "",
            "## Handoff source",
            "",
            f"- Index schema: `{index.get('schema')}`",
            f"- File count: `{index.get('file_count')}`",
            f"- Findings: `{len(index.get('findings') or [])}`",
            "",
        ]
    )


def handoff_export_manifest(files: dict[str, bytes]) -> dict[str, Any]:
    rows = []
    for path in sorted(files):
        data = files[path]
        rows.append(
            {
                "path": path,
                "content_type": _content_type(path),
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )
    manifest_body = canonical_json(rows).encode("utf-8")
    return {
        "schema": HANDOFF_EXPORT_MANIFEST_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "file_count": len(rows),
        "files": rows,
        "bundle_sha256": sha256_bytes(manifest_body),
    }


def build_handoff_export_bundle_files(bundle: dict[str, Any]) -> dict[str, bytes]:
    index = deepcopy(bundle.get("index") or {})
    summary = deepcopy(bundle.get("summary") or summarize_handoff_index(index))
    files: dict[str, bytes] = {
        "handoff_index.json": canonical_json(index).encode("utf-8"),
        "handoff_index.md": render_handoff_index_markdown(index).encode("utf-8"),
        "handoff_index_summary.json": canonical_json(summary).encode("utf-8"),
    }
    preview_bundle = {
        key: value for key, value in bundle.items() if key not in {"manifest", "files"}
    }
    files["README.md"] = _readme(preview_bundle).encode("utf-8")
    files["manifest.json"] = b"{}\n"
    manifest = handoff_export_manifest(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return {path: files[path] for path in sorted(files)}


def build_handoff_export_zip(bundle: dict[str, Any]) -> bytes:
    files = build_handoff_export_bundle_files(bundle)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_handoff_export_bundle(
    index: dict[str, Any], *, bundle_name: str | None = None
) -> dict[str, Any]:
    handoff_index = deepcopy(index or {})
    bundle: dict[str, Any] = {
        "schema": HANDOFF_EXPORT_BUNDLE_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "bundle_name": safe_handoff_bundle_name(bundle_name),
        "recommended_action": handoff_index.get("recommended_action"),
        "verification_status": handoff_index.get("verification_status"),
        "certificate_status": handoff_index.get("certificate_status"),
        "index": handoff_index,
        "summary": summarize_handoff_index(handoff_index),
        "manifest": {},
        "files": [],
    }
    files = build_handoff_export_bundle_files(bundle)
    manifest = handoff_export_manifest(files)
    bundle["manifest"] = manifest
    bundle["files"] = manifest["files"]
    return bundle


def build_handoff_export_bundle_from_verification_report(
    verification_report: dict[str, Any],
    *,
    bundle_name: str | None = None,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    index = build_handoff_index(
        deepcopy(verification_report or {}),
        bundle_name=bundle_name,
        operator=operator,
        notes=notes,
    )
    return build_handoff_export_bundle(index, bundle_name=bundle_name)
