from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from . import database
from .action_eligibility_delegate_resolution_v34_1 import (
    build_action_eligibility_delegate_resolution,
)
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.human_confirmation_framework.v34_2"
VERSION = "v35.2.0"
ISSUED_CONFIRMATION_ACTION = "governance_confirmation_issued_v35_2"


def canonical_confirmation_content(
    contract: Mapping[str, Any],
) -> dict[str, Any] | None:
    targets = contract.get("targets")
    inputs = contract.get("inputs")
    if not isinstance(targets, Mapping) or not isinstance(inputs, Mapping):
        return None
    return {
        "case_id": contract.get("case_id"),
        "action": contract.get("action"),
        "delegate_service": contract.get("delegate_service"),
        "eligibility_resolution_sha256": contract.get(
            "eligibility_resolution_sha256"
        ),
        "targets": deepcopy(dict(targets)),
        "inputs": deepcopy(dict(inputs)),
        "impact_summary": contract.get("impact_summary"),
    }


def confirmation_identity(
    contract: Mapping[str, Any],
) -> dict[str, Any] | None:
    content = canonical_confirmation_content(contract)
    if content is None:
        return None
    digest = _sha(content)
    return {
        "content": content,
        "confirmation_sha256": digest,
        "confirmation_id": f"confirm-{digest[:32]}",
    }


def record_issued_confirmation(
    contract: Mapping[str, Any],
    actor: str | None,
) -> dict[str, Any]:
    identity = confirmation_identity(contract)
    if (
        contract.get("status") != "confirmation_required"
        or identity is None
        or contract.get("confirmation_sha256")
        != identity["confirmation_sha256"]
        or contract.get("confirmation_id") != identity["confirmation_id"]
    ):
        return {
            "issued": False,
            "reason": "confirmation_binding_invalid",
            "audit_record_id": None,
        }

    database.ensure_configured()
    session = database.Session()
    digest = identity["confirmation_sha256"]
    try:
        existing = (
            session.query(database.AuditLog)
            .filter_by(
                action=ISSUED_CONFIRMATION_ACTION,
                target_value=digest,
            )
            .order_by(database.AuditLog.id.asc())
            .first()
        )
        if existing is not None:
            return {
                "issued": True,
                "reason": "already_issued",
                "audit_record_id": existing.id,
            }

        details = {
            "schema": SCHEMA,
            "version": VERSION,
            "confirmation_id": identity["confirmation_id"],
            "confirmation_sha256": digest,
            "case_id": identity["content"].get("case_id"),
            "action": identity["content"].get("action"),
            "delegate_service": identity["content"].get("delegate_service"),
            "eligibility_resolution_sha256": identity["content"].get(
                "eligibility_resolution_sha256"
            ),
        }
        record = database.AuditLog(
            actor=str(actor or "") or None,
            action=ISSUED_CONFIRMATION_ACTION,
            target_value=digest,
            details=json.dumps(details, sort_keys=True, separators=(",", ":")),
        )
        session.add(record)
        session.commit()
        return {
            "issued": True,
            "reason": "issued",
            "audit_record_id": record.id,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def issued_confirmation_record(
    contract: Mapping[str, Any],
) -> dict[str, Any] | None:
    identity = confirmation_identity(contract)
    if identity is None:
        return None
    database.ensure_configured()
    session = database.Session()
    try:
        record = (
            session.query(database.AuditLog)
            .filter_by(
                action=ISSUED_CONFIRMATION_ACTION,
                target_value=identity["confirmation_sha256"],
            )
            .order_by(database.AuditLog.id.asc())
            .first()
        )
        if record is None:
            return None
        try:
            details = json.loads(record.details or "{}")
        except (TypeError, ValueError):
            return None
        if (
            details.get("confirmation_id") != identity["confirmation_id"]
            or details.get("confirmation_sha256")
            != identity["confirmation_sha256"]
            or details.get("case_id") != identity["content"].get("case_id")
            or details.get("action") != identity["content"].get("action")
            or details.get("delegate_service")
            != identity["content"].get("delegate_service")
        ):
            return None
        return {
            "audit_record_id": record.id,
            "actor": record.actor,
            "recorded_at": (
                record.created_at.isoformat() if record.created_at else None
            ),
        }
    finally:
        session.close()


def build_confirmation_contract(
    case_id: str,
    action: str,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eligibility = build_action_eligibility_delegate_resolution(case_id)
    resolution = next(
        (
            item
            for item in eligibility.get("resolutions") or []
            if item.get("action") == action
        ),
        None,
    )
    if resolution is None or resolution.get("eligible") is not True:
        return {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "blocked",
            "case_id": case_id,
            "action": action,
            "blockers": (
                (resolution or {}).get("eligibility_blockers")
                or [{"key": "action_not_eligible"}]
            ),
            "confirmation_accepted": False,
            "execution_performed": False,
        }
    content = {
        "case_id": case_id,
        "action": action,
        "delegate_service": resolution.get("delegate_service"),
        "eligibility_resolution_sha256": resolution.get(
            "eligibility_resolution_sha256"
        ),
        "targets": resolution.get("targets") or {},
        "inputs": inputs or {},
        "impact_summary": (
            f"Confirm {action} for case {case_id} using "
            f"{resolution.get('delegate_service')}"
        ),
    }
    digest = _sha(content)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "confirmation_required",
        **content,
        "confirmation_id": f"confirm-{digest[:32]}",
        "confirmation_sha256": digest,
        "confirmation_accepted": False,
        "execution_performed": False,
        "expires_on_state_change": True,
        "duplicate_submission_protection_required": True,
    }


def validate_confirmation(
    contract: dict[str, Any],
    confirmation_id: str,
    confirmed: bool,
) -> dict[str, Any]:
    if contract.get("status") != "confirmation_required" or confirmed is not True:
        return {
            "accepted": False,
            "reason": "confirmation_invalid",
            "confirmation_sha256": contract.get("confirmation_sha256"),
        }

    identity = confirmation_identity(contract)
    if identity is None:
        return {
            "accepted": False,
            "reason": "confirmation_contract_malformed",
            "confirmation_sha256": contract.get("confirmation_sha256"),
        }

    if (
        contract.get("confirmation_sha256")
        != identity["confirmation_sha256"]
        or contract.get("confirmation_id") != identity["confirmation_id"]
        or confirmation_id != identity["confirmation_id"]
    ):
        return {
            "accepted": False,
            "reason": "confirmation_binding_invalid",
            "confirmation_sha256": contract.get("confirmation_sha256"),
            "derived_confirmation_sha256": identity["confirmation_sha256"],
        }

    issue_record = issued_confirmation_record(contract)
    if issue_record is None:
        return {
            "accepted": False,
            "reason": "confirmation_not_issued",
            "confirmation_sha256": identity["confirmation_sha256"],
        }

    return {
        "accepted": True,
        "reason": "accepted",
        "confirmation_sha256": identity["confirmation_sha256"],
        "confirmation_issue_audit": issue_record,
    }


def reset_issued_confirmations_for_tests() -> None:
    if database.Session is None:
        return
    session = database.Session()
    try:
        session.query(database.AuditLog).filter_by(
            action=ISSUED_CONFIRMATION_ACTION
        ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()
