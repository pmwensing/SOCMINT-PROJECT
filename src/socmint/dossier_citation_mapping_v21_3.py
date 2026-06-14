from __future__ import annotations

from typing import Any

from . import database
from .claim_evidence_ledger_v13 import build_claim_evidence_ledger
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_section_builder_v21_2 import build_dossier_section_draft

CITATION_MAPPING_SCHEMA = "socmint.dossier_citation_mapping.v21_3"
CITATION_SNAPSHOT_ACTION = "case_dossier_citation_mapping_snapshot"
VERSION = "v21.3.0"


def _latest_snapshot(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=CITATION_SNAPSHOT_ACTION, target_value=case_id)
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


def _evidence_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for reference in row.get("evidence_refs") or []:
            index.setdefault(str(reference), []).append(row)
        for artifact in row.get("artifact_links") or []:
            for value in (
                artifact.get("artifact_id"),
                artifact.get("path"),
                artifact.get("sha256"),
            ):
                if value is not None:
                    index.setdefault(str(value), []).append(row)
    return index


def _citation_row(label: str, claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "claim_id": claim.get("claim_id"),
        "claim_type": claim.get("claim_type"),
        "claim_value": claim.get("claim_value"),
        "source": claim.get("source"),
        "confidence": claim.get("confidence"),
        "review_state": claim.get("review_state"),
        "evidence_refs": list(claim.get("evidence_refs") or []),
        "artifact_links": list(claim.get("artifact_links") or []),
    }


def build_dossier_citation_mapping(
    case_id: str,
    *,
    subject_id: int | None,
    ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    draft = build_dossier_section_draft(case_id, subject_id=subject_id)
    if draft.get("status") == "blocked":
        return {
            "schema": CITATION_MAPPING_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "subject_id": subject_id,
            "status": "blocked",
            "blockers": draft.get("blockers") or [{"key": "draft_required"}],
            "source_records_mutated": False,
            "next_action": draft.get("next_action"),
        }
    if subject_id is None and ledger_payload is None:
        return {
            "schema": CITATION_MAPPING_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "subject_id": None,
            "status": "blocked",
            "blockers": [{"key": "subject_id_required_for_ledger_mapping"}],
            "source_records_mutated": False,
            "next_action": "select_subject_for_citation_mapping",
        }

    ledger = ledger_payload or build_claim_evidence_ledger(int(subject_id))
    rows = list(ledger.get("rows") or [])
    claims = {str(row.get("claim_id")): row for row in rows if row.get("claim_id")}
    evidence = _evidence_index(rows)
    label_by_claim = {
        claim_id: f"C{index + 1}"
        for index, claim_id in enumerate(sorted(claims))
    }
    citation_catalog = [
        _citation_row(label_by_claim[claim_id], claims[claim_id])
        for claim_id in sorted(claims)
    ]

    unresolved: list[dict[str, Any]] = []
    mapped_sections = []
    for section in draft.get("sections") or []:
        section_labels: list[str] = []
        mapped_findings = []
        for finding in section.get("findings") or []:
            provenance = finding.get("provenance") or {}
            claim_ids = [str(value) for value in provenance.get("claim_ids") or []]
            evidence_ids = [str(value) for value in provenance.get("evidence_ids") or []]
            resolved_claims = [claims[value] for value in claim_ids if value in claims]
            missing_claims = [value for value in claim_ids if value not in claims]
            resolved_evidence = {
                value: evidence.get(value, []) for value in evidence_ids if evidence.get(value)
            }
            missing_evidence = [value for value in evidence_ids if value not in evidence]
            labels = [label_by_claim[str(row["claim_id"])] for row in resolved_claims]
            section_labels.extend(labels)
            for value in missing_claims:
                unresolved.append(
                    {
                        "key": "unresolved_claim",
                        "section_id": section["section_id"],
                        "finding_id": finding.get("finding_id"),
                        "reference": value,
                    }
                )
            for value in missing_evidence:
                unresolved.append(
                    {
                        "key": "unresolved_evidence",
                        "section_id": section["section_id"],
                        "finding_id": finding.get("finding_id"),
                        "reference": value,
                    }
                )
            marker = " ".join(f"[{label}]" for label in labels)
            mapped_findings.append(
                {
                    **finding,
                    "citation_labels": labels,
                    "resolved_claim_count": len(resolved_claims),
                    "resolved_evidence_count": len(resolved_evidence),
                    "unresolved_claim_ids": missing_claims,
                    "unresolved_evidence_ids": missing_evidence,
                    "citation_ready_text": (
                        f"{finding.get('text', '').strip()} {marker}".strip()
                    ),
                }
            )
        unique_labels = sorted(set(section_labels), key=lambda value: int(value[1:]))
        section_marker = " ".join(f"[{label}]" for label in unique_labels)
        narrative = str(section.get("narrative") or "").strip()
        mapped_sections.append(
            {
                **section,
                "findings": mapped_findings,
                "citation_labels": unique_labels,
                "citation_ready_narrative": (
                    f"{narrative} {section_marker}".strip()
                ),
                "citations_complete": all(
                    not finding["unresolved_claim_ids"]
                    and not finding["unresolved_evidence_ids"]
                    for finding in mapped_findings
                ),
            }
        )

    citation_content = {
        "case_id": case_id,
        "subject_id": subject_id,
        "draft_id": draft.get("draft_id"),
        "draft_sha256": draft.get("draft_sha256"),
        "ledger_schema": ledger.get("schema"),
        "sections": mapped_sections,
        "citation_catalog": citation_catalog,
        "unresolved": unresolved,
    }
    mapping_sha256 = _sha(citation_content)
    return {
        "schema": CITATION_MAPPING_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "citation_ready" if not unresolved else "unresolved_citations",
        "mapping_id": f"citation-map-{mapping_sha256[:24]}",
        "mapping_sha256": mapping_sha256,
        "draft_id": draft.get("draft_id"),
        "draft_sha256": draft.get("draft_sha256"),
        "ledger_schema": ledger.get("schema"),
        "ledger_subject_exists": ledger.get("subject_exists", True),
        "citation_catalog": citation_catalog,
        "citation_count": len(citation_catalog),
        "sections": mapped_sections,
        "unresolved": unresolved,
        "unresolved_count": len(unresolved),
        "source_package_mutated": False,
        "draft_snapshot_mutated": False,
        "latest_snapshot": _latest_snapshot(case_id),
        "next_action": (
            "review_citation_ready_dossier"
            if not unresolved
            else "resolve_dossier_citations"
        ),
    }


def save_citation_mapping_snapshot(
    case_id: str,
    *,
    subject_id: int,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    mapping = build_dossier_citation_mapping(case_id, subject_id=subject_id)
    if mapping.get("status") == "blocked":
        return mapping
    event = {
        "schema": "socmint.dossier_citation_mapping_snapshot.v21_3",
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "mapping_id": mapping["mapping_id"],
        "mapping_sha256": mapping["mapping_sha256"],
        "draft_id": mapping["draft_id"],
        "draft_sha256": mapping["draft_sha256"],
        "citation_count": mapping["citation_count"],
        "unresolved_count": mapping["unresolved_count"],
        "sections": mapping["sections"],
        "citation_catalog": mapping["citation_catalog"],
        "source_package_mutated": False,
        "draft_snapshot_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=CITATION_SNAPSHOT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        recorded_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "saved",
        "snapshot_record_id": record_id,
        "snapshot_by": actor,
        "snapshot_at": recorded_at,
        "next_action": mapping["next_action"],
    }
