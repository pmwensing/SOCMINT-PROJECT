from __future__ import annotations

import inspect
from typing import Any, Callable

from . import database
from .action_eligibility_delegate_resolution_v34_1 import DELEGATE_REGISTRY
from .case_centric_operator_workspace_v33_6 import (
    build_case_centric_operator_workspace,
)
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage

CLAIM_ACTION = "v34_confirmation_claimed"
RESULT_ACTION = "v34_governance_action_executed"


def confirmation_claimed(confirmation_sha256: str) -> bool:
    _ensure_storage()
    session = database.Session()
    try:
        return (
            session.query(database.AuditLog)
            .filter_by(action=CLAIM_ACTION, target_value=confirmation_sha256)
            .first()
            is not None
        )
    finally:
        session.close()


def claim_confirmation(
    *, confirmation_sha256: str, actor: str, case_id: str, action: str
) -> dict[str, Any] | None:
    _ensure_storage()
    session = database.Session()
    try:
        existing = (
            session.query(database.AuditLog)
            .filter_by(action=CLAIM_ACTION, target_value=confirmation_sha256)
            .first()
        )
        if existing is not None:
            return None
        row = database.AuditLog(
            actor=actor,
            action=CLAIM_ACTION,
            target_value=confirmation_sha256,
            details=_canonical(
                {
                    "case_id": case_id,
                    "governance_action": action,
                    "confirmation_sha256": confirmation_sha256,
                    "durable_replay_claim": True,
                }
            ),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "audit_record_id": row.id,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def record_execution_result(
    *,
    actor: str,
    case_id: str,
    action: str,
    confirmation_sha256: str,
    delegate_service: str,
    result_reference_sha256: str,
    authoritative_record_ids: dict[str, Any],
) -> dict[str, Any]:
    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=RESULT_ACTION,
            target_value=case_id,
            details=_canonical(
                {
                    "case_id": case_id,
                    "governance_action": action,
                    "confirmation_sha256": confirmation_sha256,
                    "delegate_service": delegate_service,
                    "result_reference_sha256": result_reference_sha256,
                    "authoritative_record_ids": authoritative_record_ids,
                }
            ),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "audit_record_id": row.id,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
        }
    finally:
        session.close()


def authoritative_record_ids(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    return {
        key: value
        for key, value in result.items()
        if (key == "id" or key.endswith("_id") or key == "audit_record_id")
        and value not in (None, "")
    }


def audit_delegate_signatures(
    delegates: dict[str, Callable[..., Any]],
) -> dict[str, Any]:
    checks = []
    for action, registration in sorted(DELEGATE_REGISTRY.items()):
        service = str(registration["delegate_service"])
        delegate = delegates.get(service)
        missing = []
        if delegate is None:
            missing = ["delegate_unavailable"]
        else:
            parameters = inspect.signature(delegate).parameters
            accepts_kwargs = any(
                item.kind == inspect.Parameter.VAR_KEYWORD
                for item in parameters.values()
            )
            if not accepts_kwargs:
                missing = [
                    target
                    for target in registration["required_targets"]
                    if target not in parameters
                ]
        checks.append(
            {
                "action": action,
                "delegate_service": service,
                "compatible": not missing,
                "missing_parameters": missing,
            }
        )
    return {
        "status": "passed" if all(item["compatible"] for item in checks) else "failed",
        "checks": checks,
        "compatible_count": sum(item["compatible"] for item in checks),
        "delegate_count": len(checks),
    }


def refreshed_workspace(case_id: str) -> dict[str, Any]:
    return build_case_centric_operator_workspace(case_id)


def reset_execution_ledger_for_tests() -> None:
    _ensure_storage()
    session = database.Session()
    try:
        session.query(database.AuditLog).filter(
            database.AuditLog.action.in_((CLAIM_ACTION, RESULT_ACTION))
        ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()
