from __future__ import annotations

from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha
from .dossier_citation_mapping_v21_3 import build_dossier_citation_mapping
from .dossier_quality_review_v21_4 import build_dossier_quality_review
from .dossier_section_builder_v21_2 import build_dossier_section_draft
from .dossier_supervisor_approval_v21_5 import APPROVAL_ACTION, _latest_decision

FINAL_EXPORT_SCHEMA = "socmint.dossier_final_export_package.v21_6"
FINAL_EXPORT_ACTION = "case_dossier_final_export_package"
VERSION = "v21.6.0"


def _latest_export(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=FINAL_EXPORT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "export_record_id": row.id,
            "exported_by": row.actor,
            "exported_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def build_final_export_package(
    case_id: str,
    *,
    subject_id: int | None,
    ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    approval = _latest_decision(case_id)
    if approval is None:
        return {
            "schema": FINAL_EXPORT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "supervisor_approval_required"}],
            "next_action": "record_supervisor_decision",
        }
    if approval.get("result_status") in {"returned", "held"}:
        return {
            "schema": FINAL_EXPORT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": f"latest_supervisor_decision_{approval['result_status']}"}],
            "approval_record": approval,
            "next_action": approval.get("export_preparation", {}).get("next_action"),
        }
    if approval.get("result_status") != "approved":
        return {
            "schema": FINAL_EXPORT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "latest_supervisor_approval_invalid"}],
        }

    draft = build_dossier_section_draft(case_id, subject_id=subject_id)
    citations = build_dossier_citation_mapping(
        case_id, subject_id=subject_id, ledger_payload=ledger_payload
    )
    review = build_dossier_quality_review(
        case_id, subject_id=subject_id, ledger_payload=ledger_payload
    )
    if draft.get("status") == "blocked" or citations.get("status") == "blocked" or not review.get("ready"):
        return {
            "schema": FINAL_EXPORT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "current_dossier_not_export_ready"}],
            "next_action": review.get("next_action") or "resolve_dossier_quality_blockers",
        }
    if (
        approval.get("source_review_id") != review.get("review_id")
        or approval.get("source_review_sha256") != review.get("review_sha256")
    ):
        return {
            "schema": FINAL_EXPORT_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "supervisor_approval_stale"}],
            "approval_record": approval,
            "current_review_id": review.get("review_id"),
            "current_review_sha256": review.get("review_sha256"),
            "next_action": "request_supervisor_dossier_approval",
        }

    dossier_content = {
        "sections": citations.get("sections") or [],
        "section_count": len(citations.get("sections") or []),
        "draft_id": draft.get("draft_id"),
        "draft_sha256": draft.get("draft_sha256"),
        "mapping_id": citations.get("mapping_id"),
        "mapping_sha256": citations.get("mapping_sha256"),
    }
    source_manifest = {
        "package_id": draft.get("source_package_id"),
        "manifest_sha256": draft.get("source_manifest_sha256"),
        "import_record_id": draft.get("source_import_record_id"),
        "arrangement_record_id": draft.get("source_arrangement_record_id"),
        "arrangement_sha256": draft.get("source_arrangement_sha256"),
    }
    approval_record = {
        "approval_id": approval.get("approval_id"),
        "approval_record_id": approval.get("approval_record_id"),
        "decision_sha256": approval.get("decision_sha256"),
        "reviewer": approval.get("reviewer"),
        "decided_at": approval.get("decided_at"),
        "note": approval.get("note"),
        "source_review_id": approval.get("source_review_id"),
        "source_review_sha256": approval.get("source_review_sha256"),
    }
    export_metadata = {
        "format": "socmint-json",
        "media_type": "application/json",
        "classification": "case-dossier",
        "package_version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
    }
    package_content = {
        "case_id": case_id,
        "subject_id": subject_id,
        "dossier_content": dossier_content,
        "citation_catalog": citations.get("citation_catalog") or [],
        "source_manifest": source_manifest,
        "approval_record": approval_record,
        "quality_review": {
            "review_id": review.get("review_id"),
            "review_sha256": review.get("review_sha256"),
            "ready": review.get("ready"),
        },
        "export_metadata": export_metadata,
    }
    content_sha256 = _sha(package_content)
    integrity = {
        "content_sha256": content_sha256,
        "dossier_sha256": _sha(dossier_content),
        "citation_catalog_sha256": _sha(citations.get("citation_catalog") or []),
        "source_manifest_sha256": _sha(source_manifest),
        "approval_record_sha256": _sha(approval_record),
        "quality_review_sha256": review.get("review_sha256"),
    }
    package_sha256 = _sha({"content": package_content, "integrity": integrity})
    return {
        "schema": FINAL_EXPORT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "subject_id": subject_id,
        "status": "ready",
        "export_package_id": f"dossier-export-{package_sha256[:24]}",
        "export_package_sha256": package_sha256,
        **package_content,
        "integrity": integrity,
        "latest_export": _latest_export(case_id),
        "source_records_mutated": False,
        "next_action": "generate_final_export_package",
    }


def generate_final_export_package(
    case_id: str,
    *,
    subject_id: int,
    actor: str,
    ledger_payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> dict[str, Any]:
    package = build_final_export_package(
        case_id, subject_id=subject_id, ledger_payload=ledger_payload
    )
    if package.get("status") != "ready":
        return package
    event = {
        key: value for key, value in package.items() if key not in {"latest_export", "status", "next_action"}
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=FINAL_EXPORT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        exported_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "generated",
        "export_record_id": record_id,
        "exported_by": actor,
        "exported_at": exported_at,
        "next_action": "handoff_final_export_package",
    }
