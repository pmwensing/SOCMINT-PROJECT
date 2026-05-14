from __future__ import annotations

from pathlib import Path
from typing import Any

from .dossier_export_certification import export_certification_summary
from .dossier_export_index import iter_export_manifests
from .dossier_export_store import DEFAULT_EXPORT_ROOT

DOSSIER_EXPORT_CERTIFICATION_INDEX_SCHEMA = "socmint.dossier_export_certification_index.v10_12_0"


def certification_index(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    manifests = iter_export_manifests(root=root)
    entries = []
    for manifest in manifests:
        subject_id = manifest.get("subject_id")
        case_id = manifest.get("case_id")
        if not subject_id or not case_id:
            entries.append(
                {
                    "status": "invalid_manifest",
                    "certified": False,
                    "subject_id": subject_id,
                    "case_id": case_id,
                    "manifest_path": manifest.get("manifest_path"),
                    "review_items": ["missing_subject_or_case"],
                }
            )
            continue
        summary = export_certification_summary(subject_id=str(subject_id), case_id=str(case_id), root=root)
        entries.append(
            {
                "status": summary.get("status"),
                "certified": summary.get("certified"),
                "subject_id": summary.get("subject_id"),
                "case_id": summary.get("case_id"),
                "decision": summary.get("decision"),
                "review_items": summary.get("blockers", []),
                "verification_status": summary.get("verification_status"),
                "audit_event_count": summary.get("audit_event_count", 0),
                "artifact_count": summary.get("artifact_count", 0),
                "manifest_path": manifest.get("manifest_path"),
            }
        )
    certified_count = sum(1 for entry in entries if entry.get("certified") is True)
    review_count = sum(1 for entry in entries if entry.get("certified") is not True)
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_INDEX_SCHEMA,
        "status": "ready",
        "export_count": len(entries),
        "certified_count": certified_count,
        "review_count": review_count,
        "entries": entries,
    }


def certification_index_summary(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    index = certification_index(root=root)
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_INDEX_SCHEMA,
        "status": index["status"],
        "export_count": index["export_count"],
        "certified_count": index["certified_count"],
        "review_count": index["review_count"],
        "ready_for_release": index["export_count"] > 0 and index["review_count"] == 0,
    }


def certification_index_review_items(root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    index = certification_index(root=root)
    review_entries = [entry for entry in index["entries"] if entry.get("certified") is not True]
    return {
        "schema": DOSSIER_EXPORT_CERTIFICATION_INDEX_SCHEMA,
        "status": "clear" if not review_entries else "needs_review",
        "review_count": len(review_entries),
        "review_entries": review_entries,
    }
