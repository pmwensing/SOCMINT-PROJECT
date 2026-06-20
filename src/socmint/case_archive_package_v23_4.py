from __future__ import annotations

from typing import Any

from . import database
from .case_closure_decision_v23_2 import latest_supervisor_closure_decision
from .case_closure_readiness_review_v23_1 import latest_closure_readiness_review
from .case_retention_assignment_v23_3 import latest_retention_assignment
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)
from .dossier_final_export_package_v21_6 import _latest_export
from .dossier_release_history_v22_6 import build_release_delivery_history

SCHEMA = "socmint.case_archive_package.v23_4"
VERSION = "v23.4.0"
ACTION = "case_archive_package_generated"


def latest_case_archive_package(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "archive_record_id": row.id,
            "generated_by": row.actor,
            "generated_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _audit_references(case_id: str) -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value == case_id)
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        return [
            {
                "audit_record_id": row.id,
                "action": row.action,
                "actor": row.actor,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "details_sha256": _sha(_json_details(row)),
            }
            for row in rows
        ]
    finally:
        session.close()


def build_case_archive_package(case_id: str) -> dict[str, Any]:
    assignment = latest_retention_assignment(case_id)
    if assignment is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "retention_assignment_required"}],
        }
    if assignment.get("ready_for_archive_package") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "valid_retention_assignment_required"}],
            "retention_assignment": assignment,
        }

    closure_decision = latest_supervisor_closure_decision(case_id)
    readiness_review = latest_closure_readiness_review(case_id)
    final_export = _latest_export(case_id)
    release_history = build_release_delivery_history(case_id)
    audit_references = _audit_references(case_id)

    missing = []
    if closure_decision is None:
        missing.append({"key": "closure_decision_required"})
    if readiness_review is None:
        missing.append({"key": "closure_readiness_review_required"})
    if final_export is None:
        missing.append({"key": "final_dossier_export_required"})
    if release_history.get("closure_ready") is not True:
        missing.append({"key": "release_delivery_closure_required"})
    if missing:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": missing,
            "retention_assignment": assignment,
        }

    components = {
        "closure": {
            "readiness_review": readiness_review,
            "supervisor_decision": closure_decision,
        },
        "retention": assignment,
        "dossier": final_export,
        "release_delivery": {
            "closure_summary": release_history.get("closure_summary"),
            "timeline": release_history.get("timeline") or [],
        },
        "audit_references": audit_references,
    }
    component_hashes = {
        "closure_sha256": _sha(components["closure"]),
        "retention_sha256": _sha(components["retention"]),
        "dossier_sha256": _sha(components["dossier"]),
        "release_delivery_sha256": _sha(components["release_delivery"]),
        "audit_references_sha256": _sha(components["audit_references"]),
    }
    package_content = {
        "case_id": case_id,
        "components": components,
        "component_hashes": component_hashes,
        "archive_metadata": {
            "format": "socmint-case-archive-json",
            "media_type": "application/json",
            "archive_class": (assignment.get("disposition") or {}).get("archive_class"),
            "retention_disposition": (assignment.get("disposition") or {}).get(
                "disposition"
            ),
            "retention_expires_at": (assignment.get("disposition") or {}).get(
                "retention_expires_at"
            ),
            "legal_hold": (assignment.get("disposition") or {}).get("legal_hold")
            is True,
            "package_version": VERSION,
        },
    }
    package_sha256 = _sha(package_content)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": "ready",
        "archive_package_id": f"case-archive-{package_sha256[:24]}",
        "archive_package_sha256": package_sha256,
        **package_content,
        "source_records_mutated": False,
        "closure_records_mutated": False,
        "retention_assignment_mutated": False,
        "dossier_records_mutated": False,
        "release_delivery_records_mutated": False,
        "next_action": "generate_case_archive_package",
    }


def generate_case_archive_package(
    case_id: str,
    *,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    package = build_case_archive_package(case_id)
    if package.get("status") != "ready":
        return package
    event = {
        key: value
        for key, value in package.items()
        if key not in {"status", "next_action"}
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        generated_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()
    return {
        **event,
        "status": "archive_package_generated",
        "archive_record_id": record_id,
        "generated_by": actor,
        "generated_at": generated_at,
        "next_action": "manage_case_reopen_requests",
    }
