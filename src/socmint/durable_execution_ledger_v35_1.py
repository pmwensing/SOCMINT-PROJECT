from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint, or_, update
from sqlalchemy.exc import IntegrityError

from . import database
from .dossier_assembly_workspace_v21_0 import _canonical, _sha

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


class GovernanceExecution(database.Base):
    __tablename__ = "governance_executions"
    __table_args__ = (
        UniqueConstraint(
            "execution_id", name="uq_governance_executions_execution_id"
        ),
        UniqueConstraint(
            "confirmation_sha256",
            name="uq_governance_executions_confirmation_sha256",
        ),
        Index(
            "ix_governance_executions_case_state",
            "case_id",
            "current_state",
        ),
        Index("ix_governance_executions_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True)
    execution_id = Column(String(64), nullable=False)
    confirmation_sha256 = Column(String(128), nullable=False)
    case_id = Column(String(255), nullable=False)
    governance_action = Column(String(128), nullable=False)
    delegate_service = Column(String(255), nullable=False)
    current_state = Column(String(32), nullable=False)
    state_version = Column(Integer, nullable=False, default=0)
    last_actor = Column(String(255), nullable=False)
    last_reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=database.utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=database.utc_now,
        onupdate=database.utc_now,
        nullable=False,
    )


class ExecutionLedgerError(ValueError):
    """Base error for rejected durable execution-ledger operations."""


class ExecutionNotFound(ExecutionLedgerError):
    """Raised when an execution identifier has no durable ledger record."""


class ExecutionStateConflict(ExecutionLedgerError):
    """Raised when expected state/version does not match durable state."""


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


def _ensure_execution_storage() -> None:
    database.ensure_configured()
    GovernanceExecution.__table__.create(bind=database.engine, checkfirst=True)
    database.AuditLog.__table__.create(bind=database.engine, checkfirst=True)


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


def _history(session, execution_id: str) -> list[dict[str, Any]]:
    rows = (
        session.query(database.AuditLog)
        .filter_by(action=LEDGER_ACTION, target_value=execution_id)
        .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
        .all()
    )
    return [
        {
            **_details(row),
            "ledger_record_id": row.id,
            "recorded_at": row.created_at.isoformat() if row.created_at else None,
            "recorded_by": row.actor,
        }
        for row in rows
    ]


def _snapshot(session, row: GovernanceExecution) -> dict[str, Any]:
    history = _history(session, row.execution_id)
    latest = history[-1] if history else {}
    ledger_consistent = bool(
        history
        and latest.get("state") == row.current_state
        and latest.get("state_version") == row.state_version
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "execution_record_id": row.id,
        "execution_id": row.execution_id,
        "case_id": row.case_id,
        "governance_action": row.governance_action,
        "confirmation_sha256": row.confirmation_sha256,
        "delegate_service": row.delegate_service,
        "state": row.current_state,
        "state_version": row.state_version,
        "last_actor": row.last_actor,
        "last_reason": row.last_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "event_count": len(history),
        "latest_ledger_record_id": latest.get("ledger_record_id"),
        "latest_recorded_at": latest.get("recorded_at"),
        "ledger_consistent": ledger_consistent,
        "automatic_retry": False,
        "history": history,
    }


def execution_snapshot(execution_id: str) -> dict[str, Any] | None:
    _ensure_execution_storage()
    session = database.Session()
    try:
        row = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=_required(execution_id, "execution_id"))
            .first()
        )
        return _snapshot(session, row) if row is not None else None
    finally:
        session.close()


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
    requested_execution_id = execution_id_for(
        confirmation_sha256=confirmation_sha256,
        case_id=case_id,
        governance_action=governance_action,
        delegate_service=delegate_service,
    )
    reason = "confirmed_action_accepted"

    _ensure_execution_storage()
    session = database.Session()
    try:
        row = GovernanceExecution(
            execution_id=requested_execution_id,
            confirmation_sha256=confirmation_sha256,
            case_id=case_id,
            governance_action=governance_action,
            delegate_service=delegate_service,
            current_state="pending",
            state_version=0,
            last_actor=actor,
            last_reason=reason,
        )
        payload = {
            "schema": SCHEMA,
            "version": VERSION,
            "event_type": "execution_created",
            "execution_id": requested_execution_id,
            "case_id": case_id,
            "governance_action": governance_action,
            "confirmation_sha256": confirmation_sha256,
            "delegate_service": delegate_service,
            "previous_state": None,
            "state": "pending",
            "state_version": 0,
            "reason": reason,
            "automatic_retry": False,
            "retry_authorized": False,
        }
        event = database.AuditLog(
            actor=actor,
            action=LEDGER_ACTION,
            target_value=requested_execution_id,
            details=_canonical(payload),
        )
        session.add_all((row, event))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = (
                session.query(GovernanceExecution)
                .filter(
                    or_(
                        GovernanceExecution.execution_id == requested_execution_id,
                        GovernanceExecution.confirmation_sha256
                        == confirmation_sha256,
                    )
                )
                .first()
            )
            if existing is None:
                raise
            return {
                **_snapshot(session, existing),
                "created": False,
                "replay_detected": True,
                "identity_conflict": existing.execution_id
                != requested_execution_id,
                "requested_execution_id": requested_execution_id,
            }

        session.refresh(row)
        return {
            **_snapshot(session, row),
            "created": True,
            "replay_detected": False,
            "identity_conflict": False,
            "requested_execution_id": requested_execution_id,
        }
    finally:
        session.close()


def _transition_statement(
    *,
    execution_id: str,
    expected_state: str,
    expected_version: int,
    new_state: str,
    actor: str,
    reason: str,
):
    return (
        update(GovernanceExecution)
        .where(
            GovernanceExecution.execution_id == execution_id,
            GovernanceExecution.current_state == expected_state,
            GovernanceExecution.state_version == expected_version,
        )
        .values(
            current_state=new_state,
            state_version=expected_version + 1,
            last_actor=actor,
            last_reason=reason,
            updated_at=database.utc_now(),
        )
    )


def transition_execution(
    *,
    execution_id: str,
    expected_state: str,
    new_state: str,
    actor: str,
    reason: str,
    expected_version: int | None = None,
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
    if new_state not in ALLOWED_TRANSITIONS[expected_state]:
        raise InvalidExecutionTransition(
            f"transition {expected_state} -> {new_state} is not allowed"
        )

    _ensure_execution_storage()
    session = database.Session()
    try:
        row = (
            session.query(GovernanceExecution)
            .filter_by(execution_id=execution_id)
            .first()
        )
        if row is None:
            raise ExecutionNotFound(execution_id)
        durable_version = int(row.state_version)
        if row.current_state != expected_state:
            raise ExecutionStateConflict(
                f"expected {expected_state}, durable state is {row.current_state}"
            )
        if expected_version is not None and int(expected_version) != durable_version:
            raise ExecutionStateConflict(
                f"expected version {expected_version}, durable version is {durable_version}"
            )
        compare_version = durable_version if expected_version is None else int(expected_version)
        next_version = compare_version + 1

        result = session.execute(
            _transition_statement(
                execution_id=execution_id,
                expected_state=expected_state,
                expected_version=compare_version,
                new_state=new_state,
                actor=actor,
                reason=reason,
            )
        )
        if result.rowcount != 1:
            session.rollback()
            raise ExecutionStateConflict(
                "durable execution state changed before transition commit"
            )

        payload = {
            "schema": SCHEMA,
            "version": VERSION,
            "event_type": "execution_state_transitioned",
            "execution_id": execution_id,
            "case_id": row.case_id,
            "governance_action": row.governance_action,
            "confirmation_sha256": row.confirmation_sha256,
            "delegate_service": row.delegate_service,
            "previous_state": expected_state,
            "state": new_state,
            "state_version": next_version,
            "reason": reason,
            "metadata": dict(metadata or {}),
            "automatic_retry": False,
            "retry_authorized": False,
        }
        session.add(
            database.AuditLog(
                actor=actor,
                action=LEDGER_ACTION,
                target_value=execution_id,
                details=_canonical(payload),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    updated = execution_snapshot(execution_id)
    if updated is None:
        raise ExecutionLedgerError("execution transition was not durable")
    return updated


def reset_execution_ledger_for_tests() -> None:
    _ensure_execution_storage()
    session = database.Session()
    try:
        session.query(database.AuditLog).filter_by(action=LEDGER_ACTION).delete(
            synchronize_session=False
        )
        session.query(GovernanceExecution).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()
