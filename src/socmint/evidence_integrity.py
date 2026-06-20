from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence_custody import chain_of_custody_report
from .evidence_custody import custody_ledger_path
from .evidence_custody import custody_payload
from .evidence_custody import verify_all_evidence
from .evidence_custody import verification_report_root
from .evidence_intake import evidence_manifest_path
from .evidence_intake import evidence_root
from .evidence_intake import list_evidence
from .evidence_links import evidence_links_payload
from .evidence_links import link_manifest_path
from .report_export_center import bundle_root


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def integrity_root() -> Path:
    root = evidence_root() / "integrity_packs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def evidence_integrity_payload(
    case_id: str | None = None,
    subject_id: int | None = None,
) -> dict[str, Any]:
    evidence = list_evidence(case_id=case_id, subject_id=subject_id)
    custody = custody_payload()
    links = evidence_links_payload()

    total_events = custody.get("event_count", 0)
    linked_evidence_ids = {
        item.get("evidence_id")
        for item in links.get("links", [])
        if item.get("evidence_id")
    }

    missing_files = []
    for item in evidence:
        path = Path(str(item.get("path", "")))
        if not path.exists():
            missing_files.append(item)

    latest_reports = sorted(
        [
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    UTC,
                ).isoformat(),
            }
            for path in verification_report_root().glob("*")
            if path.is_file() and path.suffix.lower() in {".json", ".md"}
        ],
        key=lambda item: item["modified_at"],
        reverse=True,
    )[:20]

    return {
        "schema": "socmint.evidence_integrity_dashboard.v7_4_3",
        "generated_at": utc_now(),
        "case_id": case_id,
        "subject_id": subject_id,
        "evidence_count": len(evidence),
        "custody_event_count": total_events,
        "link_count": links.get("count", 0),
        "linked_evidence_count": len(linked_evidence_ids),
        "missing_file_count": len(missing_files),
        "evidence": evidence,
        "missing_files": missing_files,
        "latest_reports": latest_reports,
        "custody_actions": custody.get("actions", []),
    }


def safe_integrity_pack_path(name: str) -> Path:
    roots = [integrity_root().resolve(), bundle_root().resolve()]
    candidate_name = Path(name).name

    for root in roots:
        path = (root / candidate_name).resolve()
        if path.exists() and path.is_file():
            if root in path.parents or path == root:
                return path

    raise FileNotFoundError(candidate_name)


def _maybe_add_file(
    zf: zipfile.ZipFile, path: Path, arcname: str | None = None
) -> bool:
    if path.exists() and path.is_file():
        zf.write(path, arcname=arcname or path.name)
        return True
    return False


def build_custody_export_pack(
    case_id: str | None = None,
    subject_id: int | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    case_part = case_id or "all"
    subject_part = str(subject_id) if subject_id is not None else "all"
    pack_id = f"custody-integrity-{case_part}-{subject_part}-{stamp}"

    hash_report = verify_all_evidence(
        case_id=case_id,
        subject_id=subject_id,
        actor=actor,
        write_report=True,
    )
    custody_report = chain_of_custody_report(write_report=True)
    dashboard_payload = evidence_integrity_payload(
        case_id=case_id,
        subject_id=subject_id,
    )

    dashboard_json = integrity_root() / f"{pack_id}-DASHBOARD.json"
    dashboard_json.write_text(json.dumps(dashboard_payload, indent=2, sort_keys=True))

    pack_manifest = {
        "schema": "socmint.custody_export_pack_manifest.v7_4_3",
        "generated_at": utc_now(),
        "pack_id": pack_id,
        "case_id": case_id,
        "subject_id": subject_id,
        "hash_report": hash_report,
        "custody_report": {
            "report_path": custody_report.get("report_path"),
            "markdown_path": custody_report.get("markdown_path"),
            "event_count": custody_report.get("event_count"),
        },
        "dashboard_path": str(dashboard_json),
        "evidence_count": dashboard_payload.get("evidence_count"),
        "custody_event_count": dashboard_payload.get("custody_event_count"),
        "link_count": dashboard_payload.get("link_count"),
        "missing_file_count": dashboard_payload.get("missing_file_count"),
    }

    manifest_path = integrity_root() / f"{pack_id}-MANIFEST.json"
    manifest_path.write_text(json.dumps(pack_manifest, indent=2, sort_keys=True))

    zip_path = integrity_root() / f"{pack_id}.zip"

    added = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in [
            manifest_path,
            dashboard_json,
            custody_ledger_path(),
            evidence_manifest_path(),
            link_manifest_path(),
            Path(str(hash_report.get("report_path", ""))),
            Path(str(hash_report.get("markdown_path", ""))),
            Path(str(custody_report.get("report_path", ""))),
            Path(str(custody_report.get("markdown_path", ""))),
        ]:
            if path and _maybe_add_file(zf, path):
                added.append(str(path))

        zf.writestr(
            "README.txt",
            "\n".join(
                [
                    "SOCMINT Evidence Integrity + Chain-of-Custody Export Pack",
                    f"Pack ID: {pack_id}",
                    f"Case ID: {case_id}",
                    f"Subject ID: {subject_id}",
                    f"Evidence count: {dashboard_payload.get('evidence_count')}",
                    (f"Custody events: {dashboard_payload.get('custody_event_count')}"),
                    f"Evidence links: {dashboard_payload.get('link_count')}",
                    f"Missing files: {dashboard_payload.get('missing_file_count')}",
                    "",
                    (
                        "This pack contains custody, hash verification, evidence, "
                        "and link manifests."
                    ),
                ]
            ),
        )
        added.append("README.txt")

    result = {
        "schema": "socmint.custody_export_pack.v7_4_3",
        "generated_at": utc_now(),
        "pack_id": pack_id,
        "case_id": case_id,
        "subject_id": subject_id,
        "zip_path": str(zip_path),
        "manifest_path": str(manifest_path),
        "dashboard_path": str(dashboard_json),
        "download_url": (f"/evidence/integrity/packs/{zip_path.name}/download"),
        "file_count": len(added),
        "files": added,
    }

    result_path = integrity_root() / f"{pack_id}-RESULT.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    result["result_path"] = str(result_path)

    return result


def list_custody_export_packs(limit: int = 100) -> list[dict[str, Any]]:
    packs = sorted(
        [
            path
            for path in integrity_root().glob("custody-integrity-*.zip")
            if path.is_file()
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return [
        {
            "name": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(
                path.stat().st_mtime,
                UTC,
            ).isoformat(),
            "download_url": f"/evidence/integrity/packs/{path.name}/download",
        }
        for path in packs[:limit]
    ]


def integrity_dashboard_payload(
    case_id: str | None = None,
    subject_id: int | None = None,
) -> dict[str, Any]:
    payload = evidence_integrity_payload(case_id=case_id, subject_id=subject_id)
    payload["packs"] = list_custody_export_packs()
    return payload
