from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .dossier_export_audit import audit_summary
from .dossier_export_index import find_export_entry
from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import export_scope_matches
from .dossier_export_store import load_export_manifest

DOSSIER_EXPORT_VERIFICATION_SCHEMA = "socmint.dossier_export_verification.v10_9_0"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact_hashes(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifest = load_export_manifest(subject_id=subject_id, case_id=case_id, root=root)
    scope = export_scope_matches(manifest, subject_id=subject_id, case_id=case_id)
    if scope["status"] != "pass":
        return {
            "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
            "status": "blocked",
            "subject_id": subject_id,
            "case_id": case_id,
            "artifact_count": 0,
            "checks": [],
            "scope": scope,
        }
    checks = []
    for artifact in manifest.get("artifacts", []):
        path = Path(str(artifact.get("path", "")))
        expected = artifact.get("sha256")
        if not path.exists():
            checks.append(
                {
                    "filename": artifact.get("filename"),
                    "path": str(path),
                    "status": "missing",
                    "expected_sha256": expected,
                    "actual_sha256": None,
                    "match": False,
                }
            )
            continue
        actual = sha256_file(path)
        checks.append(
            {
                "filename": artifact.get("filename"),
                "path": str(path),
                "status": "ok" if actual == expected else "hash_mismatch",
                "expected_sha256": expected,
                "actual_sha256": actual,
                "match": actual == expected,
            }
        )
    return {
        "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
        "status": "pass" if checks and all(item["match"] for item in checks) else "needs_review",
        "subject_id": subject_id,
        "case_id": case_id,
        "artifact_count": len(checks),
        "checks": checks,
    }


def verify_manifest_index(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifest = load_export_manifest(subject_id=subject_id, case_id=case_id, root=root)
    index_entry = find_export_entry(case_id=case_id, subject_id=subject_id, root=root)
    manifest_scope = export_scope_matches(manifest, subject_id=subject_id, case_id=case_id)
    index_scope = export_scope_matches(index_entry, subject_id=subject_id, case_id=case_id)
    manifest_present = manifest.get("status") != "missing"
    index_present = index_entry.get("status") != "missing"
    artifact_count_match = len(manifest.get("artifacts", [])) == len(index_entry.get("artifacts", []))
    subject_match = manifest.get("subject_id") == index_entry.get("subject_id")
    case_match = manifest.get("case_id") == index_entry.get("case_id")
    checks = {
        "manifest_present": manifest_present,
        "index_present": index_present,
        "manifest_scope": manifest_scope["status"] == "pass",
        "index_scope": index_scope["status"] == "pass",
        "artifact_count_match": artifact_count_match,
        "subject_match": subject_match,
        "case_match": case_match,
    }
    return {
        "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
        "status": "pass" if all(checks.values()) else "needs_review",
        "subject_id": subject_id,
        "case_id": case_id,
        "checks": checks,
        "scope": {
            "manifest": manifest_scope,
            "index": index_scope,
        },
        "manifest_path": manifest.get("manifest_path"),
        "index_manifest_path": index_entry.get("manifest_path"),
    }


def verify_audit_coverage(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    summary = audit_summary(case_id=case_id, subject_id=subject_id, root=root)
    counts = summary.get("counts", {})
    has_export_event = counts.get("export_created", 0) > 0
    return {
        "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
        "status": "pass" if has_export_event else "needs_review",
        "subject_id": subject_id,
        "case_id": case_id,
        "checks": {
            "has_export_created_event": has_export_event,
            "event_count": summary.get("event_count", 0),
        },
        "audit_summary": summary,
    }


def export_verification_report(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    hashes = verify_artifact_hashes(subject_id=subject_id, case_id=case_id, root=root)
    manifest_index = verify_manifest_index(subject_id=subject_id, case_id=case_id, root=root)
    audit = verify_audit_coverage(subject_id=subject_id, case_id=case_id, root=root)
    checks = {
        "artifact_hashes": hashes.get("status") == "pass",
        "manifest_index": manifest_index.get("status") == "pass",
        "audit_coverage": audit.get("status") == "pass",
    }
    return {
        "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
        "status": "pass" if all(checks.values()) else "needs_review",
        "subject_id": subject_id,
        "case_id": case_id,
        "checks": checks,
        "artifact_hashes": hashes,
        "manifest_index": manifest_index,
        "audit_coverage": audit,
    }


def export_verification_summary(subject_id: str, case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    report = export_verification_report(subject_id=subject_id, case_id=case_id, root=root)
    return {
        "schema": DOSSIER_EXPORT_VERIFICATION_SCHEMA,
        "status": report["status"],
        "subject_id": subject_id,
        "case_id": case_id,
        "passed_checks": sum(1 for value in report["checks"].values() if value),
        "total_checks": len(report["checks"]),
        "checks": report["checks"],
    }
