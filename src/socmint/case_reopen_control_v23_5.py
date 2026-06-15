from __future__ import annotations

from typing import Any

from . import database
from .case_archive_package_v23_4 import latest_case_archive_package
from .case_closure_decision_v23_2 import latest_supervisor_closure_decision
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _json_details, _sha

REQUEST_SCHEMA = "socmint.case_reopen_request.v23_5"
AUTH_SCHEMA = "socmint.case_reopen_authorization.v23_5"
VERSION = "v23.5.0"
REQUEST_ACTION = "case_reopen_request"
AUTH_ACTION = "case_reopen_authorization"
ALLOWED_AUTH_DECISIONS = {"authorize", "deny"}


def _latest(case_id: str, action: str) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        row = (
            session.query(database.AuditLog)
            .filter_by(action=action, target_value=case_id)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            **_json_details(row),
            "record_id": row.id,
            "actor": row.actor,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def latest_reopen_request(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, REQUEST_ACTION)


def latest_reopen_authorization(case_id: str) -> dict[str, Any] | None:
    return _latest(case_id, AUTH_ACTION)


def _source(case_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    return latest_case_archive_package(case_id), latest_supervisor_closure_decision(case_id)


def create_reopen_request(
    case_id: str,
    *,
    reason: str,
    confirmed: bool,
    requester: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {
            "schema": REQUEST_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "explicit_reopen_request_confirmation_required"}],
            "source_records_mutated": False,
        }
    normalized_reason = str(reason or "").strip()
    if not normalized_reason:
        return {
            "schema": REQUEST_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "reopen_reason_required"}],
            "source_records_mutated": False,
        }

    archive, closure = _source(case_id)
    blockers = []
    if archive is None:
        blockers.append({"key": "archive_package_required"})
    if closure is None or closure.get("decision") != "close":
        blockers.append({"key": "closed_supervisor_decision_required"})
    if blockers:
        return {
            "schema": REQUEST_SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": blockers,
            "source_records_mutated": False,
        }

    source = {
        "archive_package_id": archive.get("archive_package_id"),
        "archive_package_sha256": archive.get("archive_package_sha256"),
        "archive_record_id": archive.get("archive_record_id"),
        "closure_decision_id": closure.get("closure_decision_id"),
        "closure_decision_sha256": closure.get("closure_decision_sha256"),
        "closure_decision_record_id": closure.get("decision_record_id"),
    }
    content = {
        "case_id": case_id,
        "reason": normalized_reason,
        "note": str(note or "").strip(),
        "source": source,
        "source_sha256": _sha(source),
    }
    request_sha256 = _sha(content)
    event = {
        "schema": REQUEST_SCHEMA,
        "version": VERSION,
        **content,
        "reopen_request_id": f"reopen-request-{request_sha256[:24]}",
        "reopen_request_sha256": request_sha256,
        "authorization_required": True,
        "case_reopened": False,
        "source_records_mutated": False,
        "closed_case_mutated": False,
        "archive_package_mutated": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=requester,
            action=REQUEST_ACTION,
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
        "status": "reopen_request_recorded",
        "request_record_id": record_id,
        "requested_by": requester,
        "requested_at": recorded_at,
        "next_action": "supervisor_reopen_authorization",
    }
