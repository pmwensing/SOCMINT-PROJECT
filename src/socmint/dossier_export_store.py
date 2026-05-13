from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .dossier_export_pack import DOSSIER_EXPORT_SCHEMA
from .dossier_export_pack import build_export_pack
from .dossier_export_pack import canonical_json

DOSSIER_EXPORT_STORE_SCHEMA = "socmint.dossier_export_store.v10_5_0"
DEFAULT_EXPORT_ROOT = Path("exports/dossiers")


def safe_slug(value: str | None, fallback: str = "unknown") -> str:
    raw = value or fallback
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-._")
    return slug[:120] or fallback


def export_directory(subject_id: str | None, case_id: str | None, root: str | Path = DEFAULT_EXPORT_ROOT) -> Path:
    return Path(root) / safe_slug(case_id, "case") / safe_slug(subject_id, "subject")


def persist_export_pack(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    analyst_reviewed: bool = False,
    root: str | Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    pack = build_export_pack(subject, evidence=evidence or [], analyst_reviewed=analyst_reviewed)
    subject_id = pack.get("summary", {}).get("subject_id") or subject.get("subject_id")
    case_id = pack.get("summary", {}).get("case_id") or subject.get("case_id")
    out_dir = export_directory(subject_id, case_id, root=root)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for key, artifact in pack.get("artifacts", {}).items():
        path = out_dir / artifact["filename"]
        path.write_text(artifact["content"], encoding="utf-8")
        written.append(
            {
                "format": key,
                "path": str(path),
                "filename": artifact["filename"],
                "media_type": artifact["media_type"],
                "sha256": artifact["sha256"],
            }
        )

    manifest = {
        "schema": DOSSIER_EXPORT_STORE_SCHEMA,
        "pack_schema": DOSSIER_EXPORT_SCHEMA,
        "status": pack.get("status"),
        "subject_id": subject_id,
        "case_id": case_id,
        "directory": str(out_dir),
        "artifacts": written,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(canonical_json(manifest), encoding="utf-8")

    return {
        "schema": DOSSIER_EXPORT_STORE_SCHEMA,
        "status": pack.get("status"),
        "directory": str(out_dir),
        "manifest_path": str(manifest_path),
        "artifact_count": len(written),
        "artifacts": written,
        "pack_summary": pack.get("summary"),
    }


def load_export_manifest(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifest_path = export_directory(subject_id, case_id, root=root) / "manifest.json"
    if not manifest_path.exists():
        return {
            "schema": DOSSIER_EXPORT_STORE_SCHEMA,
            "status": "missing",
            "subject_id": subject_id,
            "case_id": case_id,
            "manifest_path": str(manifest_path),
            "artifacts": [],
        }
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def export_store_summary(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifest = load_export_manifest(subject_id, case_id, root=root)
    return {
        "schema": DOSSIER_EXPORT_STORE_SCHEMA,
        "status": manifest.get("status"),
        "subject_id": manifest.get("subject_id"),
        "case_id": manifest.get("case_id"),
        "artifact_count": len(manifest.get("artifacts", [])),
        "manifest_path": manifest.get("manifest_path") or str(export_directory(subject_id, case_id, root=root) / "manifest.json"),
    }
