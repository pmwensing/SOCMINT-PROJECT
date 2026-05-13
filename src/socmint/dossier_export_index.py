from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import DOSSIER_EXPORT_STORE_SCHEMA
from .dossier_export_store import export_directory
from .dossier_export_store import safe_slug

DOSSIER_EXPORT_INDEX_SCHEMA = "socmint.dossier_export_index.v10_6_0"
ALLOWED_DOWNLOAD_FILES = {"dossier.json", "dossier.html", "manifest.json"}


def iter_export_manifests(root: str | Path = DEFAULT_EXPORT_ROOT) -> list[dict[str, Any]]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    manifests: list[dict[str, Any]] = []
    for path in sorted(root_path.glob("*/*/manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {
                "schema": DOSSIER_EXPORT_STORE_SCHEMA,
                "status": "invalid_manifest",
                "manifest_path": str(path),
                "artifacts": [],
            }
        manifest.setdefault("manifest_path", str(path))
        manifests.append(manifest)
    return manifests


def export_index(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifests = iter_export_manifests(root=root)
    entries = []
    for manifest in manifests:
        entries.append(
            {
                "subject_id": manifest.get("subject_id"),
                "case_id": manifest.get("case_id"),
                "status": manifest.get("status"),
                "directory": manifest.get("directory"),
                "manifest_path": manifest.get("manifest_path"),
                "artifact_count": len(manifest.get("artifacts", [])),
            }
        )
    return {
        "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
        "status": "ready",
        "export_count": len(entries),
        "entries": entries,
    }


def find_export_entry(case_id: str, subject_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifest_path = export_directory(subject_id, case_id, root=root) / "manifest.json"
    if not manifest_path.exists():
        return {
            "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
            "status": "missing",
            "case_id": case_id,
            "subject_id": subject_id,
            "manifest_path": str(manifest_path),
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
        "status": manifest.get("status", "ready"),
        "case_id": manifest.get("case_id"),
        "subject_id": manifest.get("subject_id"),
        "manifest_path": str(manifest_path),
        "directory": manifest.get("directory"),
        "artifacts": manifest.get("artifacts", []),
    }


def resolve_export_download_path(
    case_id: str,
    subject_id: str,
    filename: str,
    root: str | Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    safe_filename = safe_slug(filename, "manifest.json")
    if safe_filename not in ALLOWED_DOWNLOAD_FILES:
        return {
            "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
            "status": "blocked",
            "reason": "unsupported_filename",
            "filename": filename,
        }
    directory = export_directory(subject_id, case_id, root=root).resolve()
    path = (directory / safe_filename).resolve()
    try:
        path.relative_to(directory)
    except ValueError:
        return {
            "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
            "status": "blocked",
            "reason": "path_escape",
            "filename": filename,
        }
    if not path.exists():
        return {
            "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
            "status": "missing",
            "filename": safe_filename,
            "path": str(path),
        }
    return {
        "schema": DOSSIER_EXPORT_INDEX_SCHEMA,
        "status": "ready",
        "filename": safe_filename,
        "path": str(path),
    }
