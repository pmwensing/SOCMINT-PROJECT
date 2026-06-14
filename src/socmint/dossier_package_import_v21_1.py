from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
    _v20_package,
)

DOSSIER_PACKAGE_IMPORT_SCHEMA = "socmint.dossier_package_import.v21_1"
DOSSIER_PACKAGE_IMPORT_ACTION = "case_dossier_package_import"
VERSION = "v21.1.0"


def _latest_import(case_id: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=DOSSIER_PACKAGE_IMPORT_ACTION, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "import_record_id": row.id,
            "imported_by": row.actor,
            "imported_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def inspect_dossier_package_import(case_id: str) -> dict[str, Any]:
    package = _v20_package(case_id)
    latest = _latest_import(case_id)
    findings = package.get("findings") or []
    computed_manifest = _sha(findings)
    declared_manifest = package.get("manifest_sha256")
    manifest_verified = bool(findings) and declared_manifest == computed_manifest
    package_valid = bool(
        package.get("package_id")
        and package.get("finding_count")
        and package.get("status") in {"ready", "promoted"}
        and manifest_verified
    )
    current_identity = {
        "package_id": package.get("package_id"),
        "manifest_sha256": declared_manifest,
        "finding_count": package.get("finding_count", 0),
    }
    imported_identity = {
        "package_id": latest.get("source_package_id") if latest else None,
        "manifest_sha256": latest.get("source_manifest_sha256") if latest else None,
        "finding_count": latest.get("finding_count") if latest else None,
    }
    duplicate = bool(latest and current_identity == imported_identity)
    stale = bool(latest and current_identity != imported_identity)

    if not findings:
        status = "blocked_no_package"
        blocker = "no_approved_or_promoted_findings_package"
    elif not package.get("package_id"):
        status = "blocked_missing_identity"
        blocker = "source_package_identity_missing"
    elif not manifest_verified:
        status = "blocked_manifest_mismatch"
        blocker = "source_manifest_verification_failed"
    elif duplicate:
        status = "imported_current"
        blocker = None
    elif stale:
        status = "imported_stale"
        blocker = None
    else:
        status = "available_not_imported"
        blocker = None

    return {
        "schema": DOSSIER_PACKAGE_IMPORT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "status": status,
        "package_valid": package_valid,
        "manifest_verified": manifest_verified,
        "computed_manifest_sha256": computed_manifest,
        "source_package": package,
        "source_identity": current_identity,
        "latest_import": latest,
        "imported_identity": imported_identity,
        "duplicate_import": duplicate,
        "package_stale": stale,
        "blockers": ([{"key": blocker}] if blocker else []),
        "can_import": package_valid and not duplicate,
        "can_arrange": package_valid and duplicate,
        "next_action": (
            "arrange_dossier_sections"
            if duplicate
            else "import_current_findings_package"
            if package_valid
            else "promote_approved_findings"
        ),
    }


def import_dossier_package(
    case_id: str,
    *,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    inspection = inspect_dossier_package_import(case_id)
    if not inspection["package_valid"]:
        return {
            **inspection,
            "status": "blocked",
            "next_action": inspection["next_action"],
        }
    if inspection["duplicate_import"]:
        return {
            **inspection,
            "status": "duplicate",
            "next_action": "arrange_dossier_sections",
        }

    identity = inspection["source_identity"]
    event = {
        "schema": DOSSIER_PACKAGE_IMPORT_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "source_package_id": identity["package_id"],
        "source_manifest_sha256": identity["manifest_sha256"],
        "finding_count": identity["finding_count"],
        "manifest_verified": True,
        "imported_snapshot_sha256": _sha(
            {
                "case_id": case_id,
                "source_identity": identity,
                "findings": inspection["source_package"].get("findings") or [],
            }
        ),
        "source_records_mutated": False,
        "imported_on": datetime.now(UTC).isoformat(),
    }
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=DOSSIER_PACKAGE_IMPORT_ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        import_record_id = row.id
        imported_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "imported",
        "import_record_id": import_record_id,
        "imported_by": actor,
        "imported_at": imported_at,
        "duplicate_import": False,
        "package_stale": False,
        "next_action": "arrange_dossier_sections",
        "inspection": inspect_dossier_package_import(case_id),
    }
