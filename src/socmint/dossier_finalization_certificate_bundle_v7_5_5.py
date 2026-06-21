from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_certificate_v7_5_4 import build_verification_certificate
from .dossier_finalization_certificate_v7_5_4 import render_certificate_markdown
from .dossier_finalization_certificate_v7_5_4 import summarize_certificate

CERTIFICATE_BUNDLE_SCHEMA = "socmint.v7_5_5.dossier_finalization_certificate_bundle"
CERTIFICATE_BUNDLE_MANIFEST_SCHEMA = (
    "socmint.v7_5_5.dossier_finalization_certificate_bundle_manifest"
)
APPROVED_LINE = "v7.5.5"
DEFAULT_BUNDLE_NAME = "socmint-v7.5.5-certificate-bundle"
REQUIRED_FILES = (
    "README.md",
    "certificate.json",
    "certificate.md",
    "certificate_summary.json",
    "manifest.json",
)
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_bundle_name(value: str | None) -> str:
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
    certificate = bundle.get("certificate") or {}
    return "\n".join(
        [
            "# SOCMINT v7.5.5 Certificate Bundle Export",
            "",
            f"Bundle: `{bundle.get('bundle_name')}`",
            f"Certificate status: `{bundle.get('certificate_status')}`",
            f"Certificate valid: `{bundle.get('certificate_valid')}`",
            f"Certificate SHA-256: `{bundle.get('certificate_sha256')}`",
            f"Generated at: `{bundle.get('generated_at')}`",
            "",
            "## Contents",
            "",
            "- `certificate.json` — full v7.5.4 certificate JSON.",
            "- `certificate.md` — operator-readable certificate Markdown.",
            "- `certificate_summary.json` — compact certificate summary.",
            "- `manifest.json` — bundle file list with SHA-256 hashes and sizes.",
            "- `README.md` — this operator handoff note.",
            "",
            "## Guardrails",
            "",
            "This bundle is generated in memory. It does not execute connectors, collect data, write to the database, or persist artifacts by itself.",
            "",
            "## Certificate source",
            "",
            f"- Certificate schema: `{certificate.get('schema')}`",
            f"- Verification status: `{certificate.get('verification_status')}`",
            f"- Findings: `{len(certificate.get('findings') or [])}`",
            "",
        ]
    )


def certificate_bundle_manifest(files: dict[str, bytes]) -> dict[str, Any]:
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
        "schema": CERTIFICATE_BUNDLE_MANIFEST_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "file_count": len(rows),
        "files": rows,
        "bundle_sha256": sha256_bytes(manifest_body),
    }


def build_certificate_bundle_files(bundle: dict[str, Any]) -> dict[str, bytes]:
    certificate = deepcopy(bundle.get("certificate") or {})
    summary = deepcopy(bundle.get("summary") or summarize_certificate(certificate))
    files: dict[str, bytes] = {
        "certificate.json": canonical_json(certificate).encode("utf-8"),
        "certificate.md": render_certificate_markdown(certificate).encode("utf-8"),
        "certificate_summary.json": canonical_json(summary).encode("utf-8"),
    }
    preview_bundle = {
        key: value for key, value in bundle.items() if key not in {"manifest", "files"}
    }
    files["README.md"] = _readme(preview_bundle).encode("utf-8")
    files["manifest.json"] = b"{}\n"
    manifest = certificate_bundle_manifest(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return {path: files[path] for path in sorted(files)}


def build_certificate_bundle_zip(bundle: dict[str, Any]) -> bytes:
    files = build_certificate_bundle_files(bundle)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_certificate_bundle(
    certificate: dict[str, Any],
    *,
    bundle_name: str | None = None,
) -> dict[str, Any]:
    cert = deepcopy(certificate or {})
    bundle: dict[str, Any] = {
        "schema": CERTIFICATE_BUNDLE_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "bundle_name": safe_bundle_name(bundle_name),
        "certificate_status": cert.get("status"),
        "certificate_valid": bool(cert.get("valid")),
        "certificate_sha256": cert.get("certificate_sha256"),
        "certificate": cert,
        "summary": summarize_certificate(cert),
        "manifest": {},
        "files": [],
    }
    files = build_certificate_bundle_files(bundle)
    manifest = certificate_bundle_manifest(files)
    bundle["manifest"] = manifest
    bundle["files"] = manifest["files"]
    return bundle


def build_certificate_bundle_from_verification_report(
    verification_report: dict[str, Any],
    *,
    bundle_name: str | None = None,
    packet_name: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    certificate = build_verification_certificate(
        deepcopy(verification_report or {}),
        packet_name=packet_name,
        reviewer=reviewer,
        notes=notes,
    )
    return build_certificate_bundle(certificate, bundle_name=bundle_name)
