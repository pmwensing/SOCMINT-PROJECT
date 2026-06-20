from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_closeout_report_v7_5_10 import build_closeout_report
from .dossier_finalization_closeout_report_v7_5_10 import (
    render_closeout_report_markdown,
)
from .dossier_finalization_closeout_report_v7_5_10 import summarize_closeout_report

CLOSEOUT_EXPORT_BUNDLE_SCHEMA = (
    "socmint.v7_5_11.dossier_finalization_closeout_export_bundle"
)
CLOSEOUT_EXPORT_MANIFEST_SCHEMA = (
    "socmint.v7_5_11.dossier_finalization_closeout_export_manifest"
)
APPROVED_LINE = "v7.5.11"
DEFAULT_BUNDLE_NAME = "socmint-v7.5.11-closeout-report-export"
REQUIRED_FILES = (
    "README.md",
    "closeout_report.json",
    "closeout_report.md",
    "closeout_report_summary.json",
    "manifest.json",
)
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_closeout_bundle_name(value: str | None) -> str:
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
    report = bundle.get("report") or {}
    return "\n".join(
        [
            "# SOCMINT v7.5.11 Closeout Report Export Bundle",
            "",
            f"Bundle: `{bundle.get('bundle_name')}`",
            f"Closeout action: `{bundle.get('closeout_action')}`",
            f"Verification status: `{bundle.get('verification_status')}`",
            f"Generated at: `{bundle.get('generated_at')}`",
            "",
            "## Contents",
            "",
            "- `closeout_report.json` — full v7.5.10 closeout report JSON.",
            "- `closeout_report.md` — operator-readable closeout report Markdown.",
            "- `closeout_report_summary.json` — compact closeout report summary.",
            "- `manifest.json` — bundle file list with SHA-256 hashes and sizes.",
            "- `README.md` — this operator closeout handoff note.",
            "",
            "## Guardrails",
            "",
            "This bundle is generated in memory. It does not execute connectors, collect data, write to the database, or persist artifacts by itself.",
            "",
            "## Closeout source",
            "",
            f"- Report schema: `{report.get('schema')}`",
            f"- Chain stage: `{report.get('chain_stage')}`",
            f"- Findings: `{len(report.get('findings') or [])}`",
            "",
        ]
    )


def closeout_export_manifest(files: dict[str, bytes]) -> dict[str, Any]:
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
        "schema": CLOSEOUT_EXPORT_MANIFEST_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "file_count": len(rows),
        "files": rows,
        "bundle_sha256": sha256_bytes(manifest_body),
    }


def build_closeout_export_bundle_files(bundle: dict[str, Any]) -> dict[str, bytes]:
    report = deepcopy(bundle.get("report") or {})
    summary = deepcopy(bundle.get("summary") or summarize_closeout_report(report))
    files: dict[str, bytes] = {
        "closeout_report.json": canonical_json(report).encode("utf-8"),
        "closeout_report.md": render_closeout_report_markdown(report).encode("utf-8"),
        "closeout_report_summary.json": canonical_json(summary).encode("utf-8"),
    }
    preview_bundle = {
        key: value for key, value in bundle.items() if key not in {"manifest", "files"}
    }
    files["README.md"] = _readme(preview_bundle).encode("utf-8")
    files["manifest.json"] = b"{}\n"
    manifest = closeout_export_manifest(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return {path: files[path] for path in sorted(files)}


def build_closeout_export_zip(bundle: dict[str, Any]) -> bytes:
    files = build_closeout_export_bundle_files(bundle)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_closeout_export_bundle(
    closeout_report: dict[str, Any], *, bundle_name: str | None = None
) -> dict[str, Any]:
    report = deepcopy(closeout_report or {})
    bundle: dict[str, Any] = {
        "schema": CLOSEOUT_EXPORT_BUNDLE_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "bundle_name": safe_closeout_bundle_name(bundle_name),
        "closeout_action": report.get("closeout_action"),
        "verification_status": report.get("verification_status"),
        "report": report,
        "summary": summarize_closeout_report(report),
        "manifest": {},
        "files": [],
    }
    files = build_closeout_export_bundle_files(bundle)
    manifest = closeout_export_manifest(files)
    bundle["manifest"] = manifest
    bundle["files"] = manifest["files"]
    return bundle


def build_closeout_export_bundle_from_verification_report(
    verification_report: dict[str, Any],
    *,
    bundle_name: str | None = None,
    operator: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    report = build_closeout_report(
        deepcopy(verification_report or {}), operator=operator, notes=notes
    )
    return build_closeout_export_bundle(report, bundle_name=bundle_name)
