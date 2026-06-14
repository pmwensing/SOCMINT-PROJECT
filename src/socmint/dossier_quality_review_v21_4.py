from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_citation_mapping_v21_3 import build_dossier_citation_mapping
from .dossier_section_builder_v21_2 import build_dossier_section_draft

QUALITY_REVIEW_SCHEMA = "socmint.dossier_quality_review.v21_4"
QUALITY_REVIEW_SNAPSHOT_ACTION = "case_dossier_quality_review_snapshot"
VERSION = "v21.4.0"


def _latest_snapshot(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=QUALITY_REVIEW_SNAPSHOT_ACTION, target_value=case_id)
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


def _provenance_quality(finding: dict[str, Any]) -> dict[str, Any]:
    provenance = finding.get("provenance") or {}
    checks = {
        "claims_present": bool(provenance.get("claim_ids")),
        "evidence_present": bool(provenance.get("evidence_ids")),
        "source_context_present": bool(
            provenance.get("evidence_ids")
            or provenance.get("entity_ids")
            or provenance.get("timeline_refs")
        ),
        "provenance_hash_present": bool(finding.get("provenance_sha256")),
        "confidence_present": bool(finding.get("confidence")),
    }
    return {
        **checks,
        "complete": all(checks.values()),
        "score": round(
            (sum(bool(value) for value in checks.values()) / len(checks)) * 100,
            2,
        ),
        "missing": [key for key, value in checks.items() if not value],
    }


def build_dossier_quality_review(
    case_id: str,
    *,
    subject_id: int | None,
    ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    draft = build_dossier_section_draft(case_id, subject_id=subject_id)
    if draft.get("status") == "blocked":
        return {
            "schema": QUALITY_REVIEW_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "subject_id": subject_id,
            "status": "blocked",
            "ready": False,
            "blockers": draft.get("blockers") or [{"key": "draft_required"}],
            "next_action": draft.get("next_action"),
            "source_records_mutated": False,
        }

    citations = build_dossier_citation_mapping(
        case_id,
        subject_id=subject_id,
        ledger_payload=ledger_payload,
    )
    if citations.get("status") == "blocked":
        return {
            "schema": QUALITY_REVIEW_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "subject_id": subject_id,
            "status": "blocked",
            "ready": False,
            "blockers": citations.get("blockers")
            or [{"key": "citation_mapping_required"}],
            "next_action": citations.get("next_action"),
            "source_records_mutated": False,
        }

    blockers: list[dict[str, Any]] = []
    section_reviews = []
    total_findings = 0
    provenance_complete = 0
    source_ready = 0

    citation_sections = {
        section["section_id"]: section for section in citations.get("sections") or []
    }
    for section in draft.get("sections") or []:
        if not section.get("finding_count"):
            continue
        citation_section = citation_sections.get(section["section_id"], {})
        finding_reviews = []
        for finding in citation_section.get("findings") or section.get("findings") or []:
            quality = _provenance_quality(finding)
            total_findings += 1
            provenance_complete += int(quality["complete"])
            source_ok = bool(
                finding.get("resolved_evidence_count", 0)
                or (finding.get("provenance") or {}).get("evidence_ids")
            )
            source_ready += int(source_ok)
            if not quality["complete"]:
                blockers.append(
                    {
                        "key": "provenance_incomplete",
                        "section_id": section["section_id"],
                        "finding_id": finding.get("finding_id"),
                        "missing": quality["missing"],
                    }
                )
            if not source_ok:
                blockers.append(
                    {
                        "key": "source_not_ready",
                        "section_id": section["section_id"],
                        "finding_id": finding.get("finding_id"),
                    }
                )
            finding_reviews.append(
                {
                    "finding_id": finding.get("finding_id"),
                    "provenance_quality": quality,
                    "source_ready": source_ok,
                    "citation_labels": finding.get("citation_labels") or [],
                    "unresolved_claim_ids": finding.get("unresolved_claim_ids") or [],
                    "unresolved_evidence_ids": finding.get("unresolved_evidence_ids") or [],
                }
            )

        completeness = section.get("completeness") or {}
        narrative_covered = bool(str(section.get("narrative") or "").strip())
        citations_complete = bool(citation_section.get("citations_complete"))
        if not completeness.get("complete"):
            blockers.append(
                {
                    "key": "section_incomplete",
                    "section_id": section["section_id"],
                    "missing": completeness.get("missing") or [],
                }
            )
        if not narrative_covered:
            blockers.append(
                {"key": "narrative_missing", "section_id": section["section_id"]}
            )
        if not citations_complete:
            blockers.append(
                {"key": "citations_unresolved", "section_id": section["section_id"]}
            )
        section_reviews.append(
            {
                "section_id": section["section_id"],
                "title": section["title"],
                "position": section["position"],
                "finding_count": section["finding_count"],
                "narrative_covered": narrative_covered,
                "section_completeness": completeness,
                "citations_complete": citations_complete,
                "finding_reviews": finding_reviews,
                "ready": bool(
                    completeness.get("complete")
                    and narrative_covered
                    and citations_complete
                    and all(
                        item["provenance_quality"]["complete"]
                        and item["source_ready"]
                        for item in finding_reviews
                    )
                ),
            }
        )

    for unresolved in citations.get("unresolved") or []:
        blockers.append({**unresolved, "key": unresolved.get("key", "citation_unresolved")})

    blocker_keys = sorted({blocker["key"] for blocker in blockers})
    review_content = {
        "case_id": case_id,
        "subject_id": subject_id,
        "draft_id": draft.get("draft_id"),
        "draft_sha256": draft.get("draft_sha256"),
        "mapping_id": citations.get("mapping_id"),
        "mapping_sha256": citations.get("mapping_sha256"),
        "section_reviews": section_reviews,
        "blockers": blockers,
    }
    review_sha256 = _sha(review_content)
    ready = bool(section_reviews) and not blockers
    return {
        "schema": QUALITY_REVIEW_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "review_id": f"dossier-quality-{review_sha256[:24]}",
        "review_sha256": review_sha256,
        "draft_id": draft.get("draft_id"),
        "draft_sha256": draft.get("draft_sha256"),
        "mapping_id": citations.get("mapping_id"),
        "mapping_sha256": citations.get("mapping_sha256"),
        "section_count": len(section_reviews),
        "ready_section_count": sum(1 for item in section_reviews if item["ready"]),
        "narrative_coverage_percent": (
            round(
                sum(1 for item in section_reviews if item["narrative_covered"])
                / len(section_reviews)
                * 100,
                2,
            )
            if section_reviews
            else 0.0
        ),
        "provenance_quality_percent": (
            round(provenance_complete / total_findings * 100, 2)
            if total_findings
            else 0.0
        ),
        "source_readiness_percent": (
            round(source_ready / total_findings * 100, 2)
            if total_findings
            else 0.0
        ),
        "unresolved_citation_count": citations.get("unresolved_count", 0),
        "section_reviews": section_reviews,
        "blocker_count": len(blockers),
        "blocker_keys": blocker_keys,
        "blockers": blockers,
        "source_package_mutated": False,
        "arrangement_history_mutated": False,
        "draft_snapshot_mutated": False,
        "citation_snapshot_mutated": False,
        "latest_snapshot": _latest_snapshot(case_id),
        "next_action": (
            "request_supervisor_dossier_approval"
            if ready
            else "resolve_dossier_quality_blockers"
        ),
    }


def save_dossier_quality_review_snapshot(
    case_id: str,
    *,
    subject_id: int,
    actor: str,
    ledger_payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    review = build_dossier_quality_review(
        case_id,
        subject_id=subject_id,
        ledger_payload=ledger_payload,
    )
    if review.get("status") == "blocked":
        return review
    event = {
        "schema": "socmint.dossier_quality_review_snapshot.v21_4",
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "review_id": review["review_id"],
        "review_sha256": review["review_sha256"],
        "draft_id": review["draft_id"],
        "draft_sha256": review["draft_sha256"],
        "mapping_id": review["mapping_id"],
        "mapping_sha256": review["mapping_sha256"],
        "ready": review["ready"],
        "blocker_count": review["blocker_count"],
        "blocker_keys": review["blocker_keys"],
        "section_reviews": review["section_reviews"],
        "source_package_mutated": False,
        "arrangement_history_mutated": False,
        "draft_snapshot_mutated": False,
        "citation_snapshot_mutated": False,
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=QUALITY_REVIEW_SNAPSHOT_ACTION,
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
        "next_action": review["next_action"],
    }
