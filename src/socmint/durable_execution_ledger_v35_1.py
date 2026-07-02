from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _ensure_storage, _sha

SCHEMA = "socmint.durable_execution_ledger.v35_1"
VERSION = "v35.1.0"
LEDGER_ACTION = "v35_execution_state_transition"
IDENTITY_SCHEMA = "socmint.execution_identity.v35_1"

EXECUTION_STATES = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "uncertain",
    "reconciled",
)

ALLOWED_TRANSITIONS = {
    "pending": frozenset({"running", "failed", "uncertain"}),
    "running": frozenset({"succeeded", "failed", "uncertain"}),
    "succeeded": frozenset({"reconciled"}),
    "failed": frozenset({"reconciled"}),
    "uncertain": frozenset({"reconciled"}),
    "reconciled": frozenset(),
}


class ExecutionLedgerError(ValueError):
    """Base error for rejected durable execution-ledger operations."""


class ExecutionNotFound(ExecutionLedgerError):
    """Raised when an execution identifier has no durable ledger events."""


class ExecutionStateConflict(ExecutionLedgerError):
    """Raised when the caller's expected state does not match durable state."""


class InvalidExecutionTransition(ExecutionLedgerError):
    """Raised when a requested transition violates the v35.1 state machine."""


def _required(value: Any, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ExecutionLedgerError(f"{field} is required")
    return normalized


def _details(row: database.AuditLog) -> dict[str, Any]:
    try:
        payload = json.loads(row.details or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def execution_id_for(
    *,
    confirmation_sha256: str,
    case_id: str,
    governance_action: str,
    delegate_service: str,
) -> str:
    identity = {
        "schema": IDENTITY_SCHEMA,
        "confirmation_sha256": _required(
            confirmation_sha256, "confirmation_sha256"
        ),
        "case_id": _required(case_id, "case_id"),
        "governance_action": _required(governance_action, "governance_action"),
        "delegate_service": _required(delegate_service, "delegate_service"),
    }
    return _sha(identity)


def _event_rows(execution_id: str) -> list[database.AuditLog]:
    _ensure_storage()
    session = database.Session()
    try:
        return (
            session.query(database.AuditLog)
            .filter_by(
                action=LEDGER_ACTION,
                target_value=_required(execution_id, "execution_id"),
            )
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
    finally:
        session.close()


def execution_snapshot(execution_id: str) -> dict[str, Any] | None:
    rows = _event_rows(execution_id)
    if not rows:
        return None

    history = []
    for row in rows:
        event = _details(row)
        history.append(
            {
                **event,
                "ledger_record_id": row.id,
                "recorded_at": row.created_at.isoformat() if row.created_at else None,
                "recorded_by": row.actor,
            }
        )

    latest = history[-1]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "execution_id": latest["execution_id"],
        "case_id": latest["case_id"],
        "governance_action": latest["governance_action"],
        "confirmation_sha256": latest["confirmation_sha256"],
        "delegate_service": latest["delegate_service"],
        "state": latest["state"],
        "event_count": len(history),
        "latest_ledger_record_id": latest["ledger_record_id"],
        "latest_recorded_at": latest["recorded_at"],
        "automatic_retry": False,
        "history": history,
    }


def create_execution(
    *,
    confirmation_sha256: str,
    actor: str,
    case_id: str,
    governance_action: str,
    delegate_service: str,
) -> dict[str, Any]:
    actor = _required(actor, "actor")
    confirmation_sha256 = _required(confirmation_sha256, "confirmation_sha256")
    case_id = _required(case_id, "case_id")
    governance_action = _required(governance_action, "governance_action")
    delegate_service = _required(delegate_service, "delegate_service")
    execution_id = execution_id_for(
        confirmation_sha256=confirmation_sha256,
        case_id=case_id,
        governance_action=governance_action,
        delegate_service=delegate_service,
    )

    existing = execution_snapshot(execution_id)
    if existing is not None:
        return {
            **existing,
            "created": False,
            "replay_detected": True,
        }

    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": "execution_created",
        "execution_id": execution_id,
        "case_id": case_id,
        "governance_action": governance_action,
        "confirmation_sha256": confirmation_sha256,
        "delegate_service": delegate_service,
        "previous_state": None,
        "state": "pending",
        "reason": "confirmed_action_accepted",
        "automatic_retry": False,
        "retry_authorized": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=LEDGER_ACTION,
            target_value=execution_id,
            details=_canonical(payload),
        )
        session.add(row)
        session.commit()
    finally:
        session.close()

    snapshot = execution_snapshot(execution_id)
    if snapshot is None:
        raise ExecutionLedgerError("execution ledger write was not durable")
    return {
        **snapshot,
        "created": True,
        "replay_detected": False,
    }


def transition_execution(
    *,
    execution_id: str,
    expected_state: str,
    new_state: str,
    actor: str,
    reason: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    execution_id = _required(execution_id, "execution_id")
    expected_state = _required(expected_state, "expected_state")
    new_state = _required(new_state, "new_state")
    actor = _required(actor, "actor")
    reason = _required(reason, "reason")

    if expected_state not in EXECUTION_STATES:
        raise InvalidExecutionTransition(f"unknown expected state: {expected_state}")
    if new_state not in EXECUTION_STATES:
        raise InvalidExecutionTransition(f"unknown new state: {new_state}")

    current = execution_snapshot(execution_id)
    if current is None:
        raise ExecutionNotFound(execution_id)
    if current["state"] != expected_state:
        raise ExecutionStateConflict(
            f"expected {expected_state}, durable state is {current['state']}"
        )
    if new_state not in ALLOWED_TRANSITIONS[expected_state]:
        raise InvalidExecutionTransition(
            f"transition {expected_state} -> {new_state} is not allowed"
        )

    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "event_type": "execution_state_transitioned",
        "execution_id": execution_id,
        "case_id": current["case_id"],
        "governance_action": current["governance_action"],
        "confirmation_sha256": current["confirmation_sha256"],
        "delegate_service": current["delegate_service"],
        "previous_state": expected_state,
        "state": new_state,
        "reason": reason,
        "metadata": dict(metadata or {}),
        "automatic_retry": False,
        "retry_authorized": False,
    }

    _ensure_storage()
    session = database.Session()
    try:
        row = database.AuditLog(
            actor=actor,
            action=LEDGER_ACTION,
            target_value=execution_id,
            details=_canonical(payload),
        )
        session.add(row)
        session.commit()
    finally:
        session.close()

    updated = execution_snapshot(execution_id)
    if updated is None:
        raise ExecutionLedgerError("execution transition was not durable")
    return updated


def reset_execution_ledger_for_tests() -> None:
    _ensure_storage()
    session = database.Session()
    try:
        session.query(database.AuditLog).filter_by(action=LEDGER_ACTION).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()
