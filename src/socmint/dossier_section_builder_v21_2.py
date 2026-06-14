from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_import_workspace_v21_1 import (
    build_dossier_assembly_workspace_v21_1,
)
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

DOSSIER_DRAFT_SCHEMA = "socmint.dossier_section_draft.v21_2"
DOSSIER_DRAFT_SNAPSHOT_ACTION = "case_dossier_section_draft_snapshot"
VERSION = "v21.2.0"


def _latest_snapshot(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(
                action=DOSSIER_DRAFT_SNAPSHOT_ACTION,
                target_value=case_id,
            )
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "snapshot_record_id": row.id,
            "snapshot_by": row.actor,
            "snapshot_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _ordered_findings(
    findings: list[dict[str, Any]],
    requested_order: list[str] | None,
) -> list[dict[str, Any]]:
    by_id = {str(item.get("finding_id")): item for item in findings}
    ordered_ids = [
        str(finding_id)
        for finding_id in (requested_order or [])
        if str(finding_id) in by_id
    ]
    remaining = sorted(set(by_id) - set(ordered_ids))
    return [by_id[finding_id] for finding_id in [*ordered_ids, *remaining]]


def _section_completeness(section: dict[str, Any]) -> dict[str, Any]:
    findings = section.get("findings") or []
    narrative_present = bool(str(section.get("narrative") or "").strip())
    evidence_complete = all(
        bool((finding.get("provenance") or {}).get("evidence_ids"))
        for finding in findings
    )
    citation_complete = all(
        bool((finding.get("provenance") or {}).get("claim_ids"))
        for finding in findings
    )
    source_complete = all(
        bool(
            (finding.get("provenance") or {}).get("evidence_ids")
            or (finding.get("provenance") or {}).get("entity_ids")
            or (finding.get("provenance") or {}).get("timeline_refs")
        )
        for finding in findings
    )
    checks = {
        "narrative_present": narrative_present,
        "has_findings": bool(findings),
        "evidence_complete": evidence_complete,
        "citation_complete": citation_complete,
        "source_complete": source_complete,
    }
    required = [
        checks["narrative_present"],
        checks["has_findings"],
        checks["evidence_complete"],
        checks["citation_complete"],
        checks["source_complete"],
    ]
    return {
        **checks,
        "complete": all(required),
        "score": round((sum(bool(value) for value in required) / len(required)) * 100, 2),
        "missing": [key for key, value in checks.items() if not value],
    }


def build_dossier_section_draft(
    case_id: str,
    *,
    subject_id: int | None = None,
    finding_order: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    workspace = build_dossier_assembly_workspace_v21_1(
        case_id,
        subject_id=subject_id,
    )
    arrangement = workspace.get("arrangement") or {}
    if not arrangement.get("arrangement_record_id"):
        return {
            "schema": DOSSIER_DRAFT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "saved_arrangement_required"}],
            "next_action": "save_dossier_arrangement",
            "source_records_mutated": False,
        }
    if not workspace.get("can_arrange"):
        return {
            "schema": DOSSIER_DRAFT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "current_package_import_required"}],
            "next_action": workspace.get("next_action"),
            "source_records_mutated": False,
        }

    sections = []
    for section in sorted(workspace["sections"], key=lambda item: item["position"]):
        ordered_findings = _ordered_findings(
            list(section.get("findings") or []),
            (finding_order or {}).get(section["section_id"]),
        )
        draft_section = {
            "section_id": section["section_id"],
            "title": section["title"],
            "position": section["position"],
            "narrative": str(section.get("narrative") or "").strip(),
            "findings": ordered_findings,
            "finding_order": [item["finding_id"] for item in ordered_findings],
            "finding_count": len(ordered_findings),
        }
        draft_section["completeness"] = _section_completeness(draft_section)
        sections.append(draft_section)

    substantive = [section for section in sections if section["finding_count"]]
    complete_count = sum(
        1 for section in substantive if section["completeness"]["complete"]
    )
    draft_content = {
        "case_id": case_id,
        "subject_id": subject_id,
        "source_package_id": workspace["source_identity"].get("package_id"),
        "source_manifest_sha256": workspace["source_identity"].get(
            "manifest_sha256"
        ),
        "source_import_record_id": workspace["package_import"].get(
            "latest_import", {}
        ).get("import_record_id"),
        "source_arrangement_record_id": arrangement.get("arrangement_record_id"),
        "source_arrangement_sha256": arrangement.get("arrangement_sha256"),
        "sections": sections,
    }
    draft_sha256 = _sha(draft_content)
    draft_id = f"dossier-draft-{draft_sha256[:24]}"
    draft_complete = bool(substantive) and complete_count == len(substantive)
    return {
        "schema": DOSSIER_DRAFT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "complete" if draft_complete else "incomplete",
        "draft_id": draft_id,
        "draft_sha256": draft_sha256,
        "section_count": len(sections),
        "substantive_section_count": len(substantive),
        "complete_section_count": complete_count,
        "incomplete_section_count": len(substantive) - complete_count,
        "completeness_percent": (
            round((complete_count / len(substantive)) * 100, 2)
            if substantive
            else 0.0
        ),
        "sections": sections,
        "source_package_id": draft_content["source_package_id"],
        "source_manifest_sha256": draft_content["source_manifest_sha256"],
        "source_import_record_id": draft_content["source_import_record_id"],
        "source_arrangement_record_id": draft_content[
            "source_arrangement_record_id"
        ],
        "source_arrangement_sha256": draft_content[
            "source_arrangement_sha256"
        ],
        "source_records_mutated": False,
        "latest_snapshot": _latest_snapshot(case_id),
        "next_action": (
            "review_dossier_draft"
            if draft_complete
            else "complete_dossier_sections"
        ),
    }


def save_dossier_draft_snapshot(
    case_id: str,
    *,
    actor: str,
    subject_id: int | None = None,
    finding_order: dict[str, list[str]] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    draft = build_dossier_section_draft(
        case_id,
        subject_id=subject_id,
        finding_order=finding_order,
    )
    if draft.get("status") == "blocked":
        return draft

    event = {
        "schema": "socmint.dossier_section_draft_snapshot.v21_2",
        "version": VERSION,
        "case_id": case_id,
        "draft_id": draft["draft_id"],
        "draft_sha256": draft["draft_sha256"],
        "source_package_id": draft["source_package_id"],
        "source_manifest_sha256": draft["source_manifest_sha256"],
        "source_import_record_id": draft["source_import_record_id"],
        "source_arrangement_record_id": draft["source_arrangement_record_id"],
        "source_arrangement_sha256": draft["source_arrangement_sha256"],
        "section_count": draft["section_count"],
        "complete_section_count": draft["complete_section_count"],
        "completeness_percent": draft["completeness_percent"],
        "sections": draft["sections"],
        "source_records_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=DOSSIER_DRAFT_SNAPSHOT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        snapshot_record_id = row.id
        snapshot_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "saved",
        "snapshot_record_id": snapshot_record_id,
        "snapshot_by": actor,
        "snapshot_at": snapshot_at,
        "next_action": draft["next_action"],
    }
