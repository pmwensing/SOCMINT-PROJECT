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


def _normalize_scope_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def export_scope_matches(
    manifest: dict[str, Any],
    subject_id: str | None,
    case_id: str | None,
) -> dict[str, Any]:
    expected_subject_id = _normalize_scope_value(subject_id)
    expected_case_id = _normalize_scope_value(case_id)
    actual_subject_id = _normalize_scope_value(manifest.get("subject_id"))
    actual_case_id = _normalize_scope_value(manifest.get("case_id"))
    checks = {
        "subject_match": expected_subject_id == actual_subject_id,
        "case_match": expected_case_id == actual_case_id,
    }
    return {
        "status": "pass" if all(checks.values()) else "blocked",
        "checks": checks,
        "expected_subject_id": expected_subject_id,
        "actual_subject_id": actual_subject_id,
        "expected_case_id": expected_case_id,
        "actual_case_id": actual_case_id,
    }


def require_export_scope(
    subject_id: str | None,
    case_id: str | None,
    expected_subject_id: str | None = None,
    expected_case_id: str | None = None,
) -> None:
    expected_subject_id = _normalize_scope_value(expected_subject_id)
    expected_case_id = _normalize_scope_value(expected_case_id)
    actual_subject_id = _normalize_scope_value(subject_id)
    actual_case_id = _normalize_scope_value(case_id)
    if expected_subject_id is not None and actual_subject_id != expected_subject_id:
        raise ValueError("Export subject is outside the requested subject scope.")
    if expected_case_id is not None and actual_case_id != expected_case_id:
        raise ValueError("Export case is outside the requested case scope.")


def _audit_event(*args, **kwargs):
    from .dossier_export_audit import audit_event

    return audit_event(*args, **kwargs)


def persist_export_pack(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    analyst_reviewed: bool = False,
    root: str | Path = DEFAULT_EXPORT_ROOT,
    actor: str | None = None,
    audit: bool = True,
    expected_subject_id: str | None = None,
    expected_case_id: str | None = None,
) -> dict[str, Any]:
    pack = build_export_pack(subject, evidence=evidence or [], analyst_reviewed=analyst_reviewed)
    subject_id = pack.get("summary", {}).get("subject_id") or subject.get("subject_id")
    case_id = pack.get("summary", {}).get("case_id") or subject.get("case_id")
    require_export_scope(
        subject_id=subject_id,
        case_id=case_id,
        expected_subject_id=expected_subject_id,
        expected_case_id=expected_case_id,
    )
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

    result = {
        "schema": DOSSIER_EXPORT_STORE_SCHEMA,
        "status": pack.get("status"),
        "directory": str(out_dir),
        "manifest_path": str(manifest_path),
        "artifact_count": len(written),
        "artifacts": written,
        "pack_summary": pack.get("summary"),
    }

    if audit and case_id and subject_id:
        event = _audit_event(
            "export_created",
            case_id=str(case_id),
            subject_id=str(subject_id),
            actor=actor,
            detail={
                "artifact_count": len(written),
                "status": pack.get("status"),
                "manifest_path": str(manifest_path),
            },
            root=root,
        )
        result["audit_event"] = event

    return result


def load_export_manifest(
    subject_id: str,
    case_id: str,
    root: str | Path = DEFAULT_EXPORT_ROOT,
    actor: str | None = None,
    audit: bool = False,
) -> dict[str, Any]:
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if audit:
        manifest["audit_event"] = _audit_event(
            "manifest_read",
            case_id=case_id,
            subject_id=subject_id,
            actor=actor,
            detail={"manifest_path": str(manifest_path)},
            root=root,
        )
    return manifest


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
