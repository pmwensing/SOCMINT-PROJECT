from __future__ import annotations

from pathlib import Path
from typing import Any

from .dossier_export_certification import export_certification_bundle
from .dossier_export_certification import export_certification_summary
from .dossier_export_index import iter_export_manifests
from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import load_export_manifest

DOSSIER_CERTIFICATION_INDEX_SCHEMA = "socmint.dossier_certification_index.v10_12_0"


def _artifact_status(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    attached = [
        {
            "filename": item.get("filename"),
            "media_type": item.get("media_type"),
            "path": item.get("path"),
            "sha256": item.get("sha256"),
            "hash_present": bool(item.get("sha256")),
        }
        for item in artifacts
    ]
    missing_hashes = [item.get("filename") for item in attached if not item.get("hash_present")]
    return {
        "artifact_count": len(attached),
        "hash_count": sum(1 for item in attached if item.get("hash_present")),
        "missing_hash_count": len(missing_hashes),
        "missing_hashes": missing_hashes,
        "artifacts": attached,
    }


def certification_index_entry(
    case_id: str,
    subject_id: str,
    root: str | Path = DEFAULT_EXPORT_ROOT,
) -> dict[str, Any]:
    manifest = load_export_manifest(subject_id=subject_id, case_id=case_id, root=root)
    artifacts = _artifact_status(manifest.get("artifacts", []))

    if manifest.get("status") == "missing":
        return {
            "schema": DOSSIER_CERTIFICATION_INDEX_SCHEMA,
            "status": "missing",
            "safe_to_distribute": False,
            "distribution_decision": "hold",
            "case_id": case_id,
            "subject_id": subject_id,
            "manifest_status": "missing",
            "manifest_path": manifest.get("manifest_path"),
            "directory": manifest.get("directory"),
            "artifact_count": 0,
            "artifacts": [],
            "hash_count": 0,
            "missing_hash_count": 0,
            "missing_hashes": [],
            "verification_status": "missing",
            "gate_decision": "deny",
            "certified": False,
            "certification_status": "not_certified",
            "blockers": ["missing_export_manifest"],
            "audit_event_count": 0,
            "audit_counts": {},
            "recommended_bundle": None,
        }

    bundle = export_certification_bundle(subject_id=subject_id, case_id=case_id, root=root)
    summary = export_certification_summary(subject_id=subject_id, case_id=case_id, root=root)
    certified = bool(summary.get("certified"))
    blockers = list(summary.get("blockers", []))
    recommended_bundle = str(Path(str(manifest.get("directory"))) / "manifest.json") if certified and manifest.get("directory") else None

    return {
        "schema": DOSSIER_CERTIFICATION_INDEX_SCHEMA,
        "status": "ready",
        "safe_to_distribute": certified,
        "distribution_decision": "allow" if certified else "hold",
        "case_id": case_id,
        "subject_id": subject_id,
        "manifest_status": manifest.get("status"),
        "manifest_path": manifest.get("manifest_path"),
        "directory": manifest.get("directory"),
        "artifact_count": artifacts["artifact_count"],
        "artifacts": artifacts["artifacts"],
        "hash_count": artifacts["hash_count"],
        "missing_hash_count": artifacts["missing_hash_count"],
        "missing_hashes": artifacts["missing_hashes"],
        "verification_status": summary.get("verification_status"),
        "gate_decision": summary.get("decision"),
        "certified": certified,
        "certification_status": summary.get("status"),
        "blockers": blockers,
        "audit_event_count": summary.get("audit_event_count", 0),
        "audit_counts": bundle.get("audit", {}).get("counts", {}),
        "recommended_bundle": recommended_bundle,
    }


def certification_index(case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    entries = []
    for manifest in iter_export_manifests(root=root):
        if manifest.get("case_id") != case_id:
            continue
        subject_id = manifest.get("subject_id")
        if not subject_id:
            entries.append(
                {
                    "schema": DOSSIER_CERTIFICATION_INDEX_SCHEMA,
                    "status": "invalid_manifest",
                    "safe_to_distribute": False,
                    "distribution_decision": "hold",
                    "case_id": case_id,
                    "subject_id": None,
                    "manifest_status": manifest.get("status", "invalid_manifest"),
                    "manifest_path": manifest.get("manifest_path"),
                    "artifact_count": len(manifest.get("artifacts", [])),
                    "certified": False,
                    "certification_status": "not_certified",
                    "blockers": ["missing_subject_id"],
                    "audit_event_count": 0,
                    "recommended_bundle": None,
                }
            )
            continue
        entries.append(certification_index_entry(case_id=case_id, subject_id=str(subject_id), root=root))

    safe_entries = [entry for entry in entries if entry.get("safe_to_distribute") is True]
    held_entries = [entry for entry in entries if entry.get("safe_to_distribute") is not True]
    return {
        "schema": DOSSIER_CERTIFICATION_INDEX_SCHEMA,
        "status": "ready",
        "case_id": case_id,
        "export_count": len(entries),
        "safe_to_distribute_count": len(safe_entries),
        "hold_count": len(held_entries),
        "entries": entries,
        "safe_to_distribute": safe_entries,
        "held": held_entries,
    }


def certification_index_summary(case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> dict[str, Any]:
    index = certification_index(case_id=case_id, root=root)
    blocker_counts: dict[str, int] = {}
    for entry in index["entries"]:
        for blocker in entry.get("blockers", []):
            blocker_counts[str(blocker)] = blocker_counts.get(str(blocker), 0) + 1
    return {
        "schema": DOSSIER_CERTIFICATION_INDEX_SCHEMA,
        "status": index["status"],
        "case_id": case_id,
        "export_count": index["export_count"],
        "certified_count": index["safe_to_distribute_count"],
        "not_certified_count": index["hold_count"],
        "safe_to_distribute_count": index["safe_to_distribute_count"],
        "hold_count": index["hold_count"],
        "blocker_counts": blocker_counts,
        "safe_subjects": [entry.get("subject_id") for entry in index["safe_to_distribute"]],
        "held_subjects": [entry.get("subject_id") for entry in index["held"]],
    }


def certification_index_markdown(case_id: str, root: str | Path = DEFAULT_EXPORT_ROOT) -> str:
    index = certification_index(case_id=case_id, root=root)
    summary = certification_index_summary(case_id=case_id, root=root)
    lines = [
        f"# Certification Index — {case_id}",
        "",
        f"Exports: {summary['export_count']}",
        f"Certified / safe to distribute: {summary['certified_count']}",
        f"Held for review: {summary['not_certified_count']}",
        "",
        "| Subject | Decision | Certified | Verification | Artifacts | Audit events | Blockers | Recommended bundle |",
        "|---|---:|---:|---|---:|---:|---|---|",
    ]
    for entry in index["entries"]:
        blockers = ", ".join(entry.get("blockers", [])) or "none"
        recommended = entry.get("recommended_bundle") or "hold"
        lines.append(
            "| {subject} | {decision} | {certified} | {verification} | {artifacts} | {audit} | {blockers} | {recommended} |".format(
                subject=entry.get("subject_id") or "unknown",
                decision=entry.get("distribution_decision"),
                certified=str(entry.get("certified")),
                verification=entry.get("verification_status") or "unknown",
                artifacts=entry.get("artifact_count", 0),
                audit=entry.get("audit_event_count", 0),
                blockers=blockers,
                recommended=recommended,
            )
        )
    return "\n".join(lines) + "\n"
