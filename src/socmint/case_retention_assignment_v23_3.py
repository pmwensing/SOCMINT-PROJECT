from __future__ import annotations

from datetime import datetime
from typing import Any

from . import database
from .case_closure_decision_v23_2 import latest_supervisor_closure_decision
from .case_closure_workspace_v23_0 import _retention_policies
from .dossier_assembly_workspace_v21_0 import (
    _canonical,
    _ensure_storage,
    _json_details,
    _sha,
)

SCHEMA = "socmint.case_retention_assignment.v23_3"
VERSION = "v23.3.0"
ACTION = "case_retention_policy_assignment"


def latest_retention_assignment(case_id: str) -> dict[str, Any] | None:
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
            "assignment_record_id": row.id,
            "assigned_by": row.actor,
            "assigned_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _anniversary(value: datetime, years: int) -> datetime:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _retention_disposition(
    policy: dict[str, Any], closure_decision: dict[str, Any]
) -> dict[str, Any]:
    retention_years = policy.get("retention_years")
    basis = _parse_timestamp(closure_decision.get("decided_at"))
    expires_at = None
    if isinstance(retention_years, int) and retention_years >= 0 and basis is not None:
        expires_at = _anniversary(basis, retention_years).isoformat()
    indefinite = retention_years is None
    return {
        "retention_basis": "supervisor_closure_decision_timestamp",
        "retention_basis_at": closure_decision.get("decided_at"),
        "retention_years": retention_years,
        "retention_expires_at": expires_at,
        "indefinite_retention": indefinite,
        "legal_hold": policy.get("archive_class") == "legal_hold",
        "archive_class": policy.get("archive_class"),
        "disposition": (
            "hold_until_authorized_release"
            if policy.get("archive_class") == "legal_hold"
            else "retain_indefinitely"
            if indefinite
            else "retain_until_expiration"
        ),
    }


def assign_retention_policy(
    case_id: str,
    *,
    policy_id: str,
    confirmed: bool,
    assigner: str,
    note: str = "",
    ip_address: str | None = None,
) -> dict[str, Any]:
    if confirmed is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [
                {"key": "explicit_retention_assignment_confirmation_required"}
            ],
            "source_records_mutated": False,
        }

    decision = latest_supervisor_closure_decision(case_id)
    if decision is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "supervisor_closure_decision_required"}],
            "source_records_mutated": False,
        }
    if decision.get("decision") != "close" or decision.get("case_closed") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "closed_supervisor_decision_required"}],
            "source_records_mutated": False,
        }

    policies = _retention_policies()
    selected = next(
        (
            policy
            for policy in policies
            if policy.get("policy_id") == str(policy_id or "")
        ),
        None,
    )
    if selected is None:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "case_id": case_id,
            "status": "blocked",
            "blockers": [{"key": "retention_policy_not_in_catalog"}],
            "available_policy_ids": [policy.get("policy_id") for policy in policies],
            "source_records_mutated": False,
        }

    source = {
        "closure_decision_id": decision.get("closure_decision_id"),
        "closure_decision_sha256": decision.get("closure_decision_sha256"),
        "closure_decision_record_id": decision.get("decision_record_id"),
        "closure_decision": decision.get("decision"),
        "closure_decided_by": decision.get("decided_by"),
        "closure_decided_at": decision.get("decided_at"),
        "readiness_review_id": (decision.get("source") or {}).get(
            "readiness_review_id"
        ),
    }
    disposition = _retention_disposition(selected, decision)
    content = {
        "case_id": case_id,
        "policy": dict(selected),
        "disposition": disposition,
        "note": str(note or "").strip(),
        "source": source,
        "source_sha256": _sha(source),
    }
    assignment_sha256 = _sha(content)
    event = {
        "schema": SCHEMA,
        "version": VERSION,
        **content,
        "retention_assignment_id": f"retention-assignment-{assignment_sha256[:24]}",
        "retention_assignment_sha256": assignment_sha256,
        "ready_for_archive_package": True,
        "source_records_mutated": False,
        "closure_decision_mutated": False,
        "archive_package_created": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=assigner,
            action=ACTION,
            target_value=case_id,
            ip_address=ip_address,
            details=_canonical(event),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        record_id = row.id
        assigned_at = row.created_at.isoformat() if row.created_at else None
    finally:
        session.close()

    return {
        **event,
        "status": "retention_assignment_recorded",
        "assignment_record_id": record_id,
        "assigned_by": assigner,
        "assigned_at": assigned_at,
        "next_action": "generate_case_archive_package",
    }
