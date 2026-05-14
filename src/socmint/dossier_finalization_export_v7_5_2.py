from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_v7_5_1 import build_dossier_finalization_packet
from .dossier_finalization_v7_5_1 import render_finalization_markdown
from .dossier_finalization_v7_5_1 import summarize_finalization_decision

EXPORT_PACKET_SCHEMA = "socmint.v7_5_2.dossier_finalization_export_packet"
EXPORT_MANIFEST_SCHEMA = "socmint.v7_5_2.dossier_finalization_export_manifest"
APPROVED_LINE = "v7.5.2"
DEFAULT_PACKAGE_NAME = "socmint-v7.5.2-finalization-export"
REQUIRED_FILES = (
    "README.md",
    "finalization_packet.json",
    "finalization_packet.md",
    "finalization_summary.json",
    "manifest.json",
)
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_package_name(value: str | None) -> str:
    raw = (value or DEFAULT_PACKAGE_NAME).strip().lower()
    cleaned = re.sub(r"[^a-z0-9_.-]+", "-", raw)
    cleaned = re.sub(r"-+", "-", cleaned).strip(".-_")
    return cleaned or DEFAULT_PACKAGE_NAME


def _content_type(path: str) -> str:
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".md"):
        return "text/markdown"
    if path.endswith(".txt"):
        return "text/plain"
    return "application/octet-stream"


def _readme(packet: dict[str, Any]) -> str:
    finalization = packet.get("finalization") or {}
    return "\n".join(
        [
            "# SOCMINT v7.5.2 Finalization Export Packet",
            "",
            f"Package: `{packet.get('package_name')}`",
            f"Decision: `{packet.get('decision')}`",
            f"Ready: `{packet.get('ready')}`",
            f"Generated at: `{packet.get('generated_at')}`",
            "",
            "## Contents",
            "",
            "- `finalization_packet.json` — full v7.5.1 finalization packet.",
            "- `finalization_packet.md` — operator-readable finalization packet.",
            "- `finalization_summary.json` — compact finalization decision summary.",
            "- `manifest.json` — file list with SHA-256 hashes and sizes.",
            "- `README.md` — this operator handoff note.",
            "",
            "## Guardrails",
            "",
            "This packet is generated in memory. It does not execute connectors, collect data, write to the database, or persist artifacts by itself.",
            "",
            "## Source decision",
            "",
            f"- v7.5.1 schema: `{finalization.get('schema')}`",
            f"- Blocking findings: `{finalization.get('blocking_count')}`",
            f"- Warnings: `{finalization.get('warning_count')}`",
            "",
        ]
    )


def finalization_export_manifest(files: dict[str, bytes]) -> dict[str, Any]:
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
        "schema": EXPORT_MANIFEST_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "file_count": len(rows),
        "files": rows,
        "package_sha256": sha256_bytes(manifest_body),
    }


def build_finalization_export_files(packet: dict[str, Any]) -> dict[str, bytes]:
    finalization = deepcopy(packet.get("finalization") or {})
    summary = deepcopy(packet.get("summary") or summarize_finalization_decision(finalization))
    files: dict[str, bytes] = {
        "finalization_packet.json": canonical_json(finalization).encode("utf-8"),
        "finalization_packet.md": render_finalization_markdown(finalization).encode("utf-8"),
        "finalization_summary.json": canonical_json(summary).encode("utf-8"),
    }
    preview_packet = {key: value for key, value in packet.items() if key not in {"manifest", "files"}}
    files["README.md"] = _readme(preview_packet).encode("utf-8")
    files["manifest.json"] = b"{}\n"
    manifest = finalization_export_manifest(files)
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return {path: files[path] for path in sorted(files)}


def build_finalization_export_zip(packet: dict[str, Any]) -> bytes:
    files = build_finalization_export_files(packet)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[path])
    return buffer.getvalue()


def build_finalization_export_packet(
    dossier_payload: dict[str, Any],
    *,
    connectors: list[dict[str, Any]] | None = None,
    policy_events: list[dict[str, Any]] | None = None,
    export_mode: str = "final",
    package_name: str | None = None,
) -> dict[str, Any]:
    payload = deepcopy(dossier_payload or {})
    finalization = build_dossier_finalization_packet(
        payload,
        connectors=connectors,
        policy_events=policy_events,
        export_mode=export_mode,
    )
    summary = summarize_finalization_decision(finalization)
    packet: dict[str, Any] = {
        "schema": EXPORT_PACKET_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "package_name": safe_package_name(package_name),
        "finalization": finalization,
        "summary": summary,
        "manifest": {},
        "files": [],
        "ready": bool(finalization.get("ready")),
        "decision": finalization.get("decision"),
    }
    files = build_finalization_export_files(packet)
    manifest = finalization_export_manifest(files)
    packet["manifest"] = manifest
    packet["files"] = manifest["files"]
    return packet
