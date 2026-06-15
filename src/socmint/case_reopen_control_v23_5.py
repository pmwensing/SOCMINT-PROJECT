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
