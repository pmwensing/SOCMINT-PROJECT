from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from typing import Any

from . import database
from .case_findings_v20 import build_dossier_promotion_package, list_findings

DOSSIER_ASSEMBLY_SCHEMA = "socmint.dossier_assembly_workspace.v21_0"
DOSSIER_ARRANGEMENT_ACTION = "case_dossier_assembly_arrangement"
VERSION = "v21.0.0"
DEFAULT_SECTIONS = (
    "executive_summary",
    "key_findings",
    "identity_and_entities",
    "timeline_and_activity",
    "evidence_and_sources",
    "analyst_assessment",
)


def _ensure_storage() -> None:
    database.ensure_configured()
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json_details(row) -> dict[str, Any]:
    try:
        value = json.loads(row.details or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _latest_arrangement(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter_by(action=DOSSIER_ARRANGEMENT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .all()
        )
        if not rows:
            return None
        row = rows[0]
        return {
            **_json_details(row),
            "arrangement_record_id": row.id,
            "arranged_by": row.actor,
            "arranged_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _v20_package(case_id: str) -> dict[str, Any]:
    package = build_dossier_promotion_package(case_id, actor="dossier-assembly")
    if package.get("finding_count"):
        return package

    workspace = list_findings(case_id)
    promoted = [
        finding
        for finding in workspace.get("findings", [])
        if finding.get("status") == "promoted"
    ]
    manifest = [
        {
            "finding_id": item["finding_id"],
            "text": item.get("text"),
            "confidence": item.get("confidence"),
            "provenance": deepcopy(item.get("provenance") or {}),
            "provenance_sha256": item.get("provenance_sha256"),
        }
        for item in promoted
    ]
    package_ids = sorted(
        {str(item.get("package_id")) for item in promoted if item.get("package_id")}
    )
    return {
        "schema": "socmint.case_findings_dossier_package.v20_5",
        "version": "v20.7.0",
        "case_id": case_id,
        "package_id": package_ids[-1] if package_ids else None,
        "finding_count": len(manifest),
        "findings": manifest,
        "manifest_sha256": _sha(manifest),
        "status": "promoted" if manifest else "blocked",
        "next_action": "assemble_dossier" if manifest else "approve_case_findings",
    }


def _suggested_section(finding: dict[str, Any]) -> str:
    provenance = finding.get("provenance") or {}
    if provenance.get("timeline_refs"):
        return "timeline_and_activity"
    if provenance.get("entity_ids"):
        return "identity_and_entities"
    return "key_findings"


def _integration_links(case_id: str, subject_id: int | None) -> dict[str, Any]:
    links = {
        "case_findings_workspace": f"/case-findings/{case_id}",
        "case_delivery_workspace": f"/case-delivery?case_id={case_id}",
    }
    if subject_id is not None:
        links.update(
            {
                "dossier_readiness_api": (
                    f"/api/v1/subjects/{subject_id}/dossier/readiness"
                ),
                "claim_evidence_ledger_api": (
                    f"/api/v1/subjects/{subject_id}/claim-evidence-ledger"
                ),
                "claim_evidence_ledger_ui": (
                    f"/subjects/{subject_id}/claim-evidence-ledger"
                ),
                "export_manifest_draft": (
                    f"/api/v1/subjects/{subject_id}/export-manifest-draft"
                ),
                "ultimate_dossier": (
                    f"/spine/subjects/{subject_id}/ultimate-dossier"
                ),
            }
        )
    return links


def _gap_rows(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for section in sections:
        section_id = section["section_id"]
        findings = section.get("findings") or []
        narrative = str(section.get("narrative") or "").strip()
        if findings and not narrative:
            gaps.append(
                {
                    "key": "missing_narrative",
                    "section_id": section_id,
                    "detail": "Section has findings but no operator narrative.",
                }
            )
        for finding in findings:
            provenance = finding.get("provenance") or {}
            if not provenance.get("evidence_ids"):
                gaps.append(
                    {
                        "key": "missing_evidence",
                        "section_id": section_id,
                        "finding_id": finding.get("finding_id"),
                    }
                )
            if not provenance.get("claim_ids"):
                gaps.append(
                    {
                        "key": "missing_citation",
                        "section_id": section_id,
                        "finding_id": finding.get("finding_id"),
                    }
                )
            if not (
                provenance.get("entity_ids")
                or provenance.get("timeline_refs")
                or provenance.get("evidence_ids")
            ):
                gaps.append(
                    {
                        "key": "missing_source",
                        "section_id": section_id,
                        "finding_id": finding.get("finding_id"),
                    }
                )
    return gaps


def build_dossier_assembly_workspace(
    case_id: str,
    *,
    subject_id: int | None = None,
) -> dict[str, Any]:
    package = _v20_package(case_id)
    arrangement = _latest_arrangement(case_id) or {}
    section_order = arrangement.get("section_order") or list(DEFAULT_SECTIONS)
    finding_sections = arrangement.get("finding_sections") or {}
    narratives = arrangement.get("narratives") or {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for finding in package.get("findings") or []:
        section_id = finding_sections.get(finding["finding_id"]) or _suggested_section(
            finding
        )
        grouped[section_id].append(deepcopy(finding))

    unknown_sections = sorted(set(grouped) - set(section_order))
    section_order = [*section_order, *unknown_sections]
    sections = [
        {
            "section_id": section_id,
            "title": section_id.replace("_", " ").title(),
            "position": index + 1,
            "narrative": narratives.get(section_id, ""),
            "findings": grouped.get(section_id, []),
            "finding_count": len(grouped.get(section_id, [])),
        }
        for index, section_id in enumerate(section_order)
    ]
    gaps = _gap_rows(sections)
    return {
        "schema": DOSSIER_ASSEMBLY_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "ready_for_arrangement" if package.get("finding_count") else "blocked",
        "source_package": package,
        "source_package_immutable": True,
        "source_findings_immutable": True,
        "sections": sections,
        "section_count": len(sections),
        "finding_count": package.get("finding_count", 0),
        "gaps": gaps,
        "gap_count": len(gaps),
        "gap_summary": {
            key: sum(1 for gap in gaps if gap["key"] == key)
            for key in (
                "missing_narrative",
                "missing_evidence",
                "missing_citation",
                "missing_source",
            )
        },
        "arrangement": arrangement,
        "integration_links": _integration_links(case_id, subject_id),
        "next_action": (
            "arrange_dossier_sections"
            if package.get("finding_count")
            else "promote_approved_findings"
        ),
    }


def save_dossier_arrangement(
    case_id: str,
    payload: dict[str, Any],
    *,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    workspace = build_dossier_assembly_workspace(case_id)
    valid_findings = {
        finding["finding_id"]
        for section in workspace["sections"]
        for finding in section["findings"]
    }
    section_order = [
        str(value).strip()
        for value in payload.get("section_order") or []
        if str(value).strip()
    ]
    finding_sections = {
        str(finding_id): str(section_id)
        for finding_id, section_id in (payload.get("finding_sections") or {}).items()
        if str(finding_id) in valid_findings and str(section_id).strip()
    }
    narratives = {
        str(section_id): str(narrative or "").strip()
        for section_id, narrative in (payload.get("narratives") or {}).items()
    }
    if not section_order:
        section_order = [section["section_id"] for section in workspace["sections"]]

    event = {
        "schema": "socmint.dossier_assembly_arrangement.v21_0",
        "version": VERSION,
        "case_id": case_id,
        "source_package_id": workspace["source_package"].get("package_id"),
        "source_manifest_sha256": workspace["source_package"].get(
            "manifest_sha256"
        ),
        "section_order": section_order,
        "finding_sections": finding_sections,
        "narratives": narratives,
        "arrangement_sha256": _sha(
            {
                "section_order": section_order,
                "finding_sections": finding_sections,
                "narratives": narratives,
            }
        ),
        "source_records_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=DOSSIER_ARRANGEMENT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            **event,
            "status": "saved",
            "arrangement_record_id": row.id,
            "arranged_by": row.actor,
            "arranged_at": row.created_at.isoformat() if row.created_at else None,
            "workspace": build_dossier_assembly_workspace(case_id),
        }
    finally:
        session.close()
