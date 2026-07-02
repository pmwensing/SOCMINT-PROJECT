from __future__ import annotations

import json
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from . import database

SCHEMA = "socmint.governance_execution_result_envelope.v35_3"
VERSION = "v35.3.0"
RESULT_IDENTITY_SCHEMA = "socmint.governance_execution_result_identity.v35_3"


class GovernanceExecutionResult(database.Base):
    __tablename__ = "governance_execution_results"
    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            name="uq_governance_execution_results_execution_id",
        ),
        UniqueConstraint(
            "result_envelope_sha256",
            name="uq_governance_execution_results_envelope_sha256",
        ),
        Index(
            "ix_governance_execution_results_case_action",
            "case_id",
            "governance_action",
        ),
        Index(
            "ix_governance_execution_results_recorded_at",
            "recorded_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    execution_id = Column(
        String(64),
        ForeignKey("governance_executions.execution_id", ondelete="CASCADE"),
        nullable=False,
    )
    confirmation_sha256 = Column(String(128), nullable=False)
    confirmation_issue_audit_id = Column(
        Integer,
        ForeignKey("audit_logs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contract_validation_sha256 = Column(String(128), nullable=False)
    case_id = Column(String(255), nullable=False)
    governance_action = Column(String(128), nullable=False)
    delegate_service = Column(String(255), nullable=False)
    authoritative_record_ids = Column(Text, nullable=False)
    result_reference_sha256 = Column(String(128), nullable=False)
    final_state = Column(String(32), nullable=False)
    state_version = Column(Integer, nullable=False)
    workspace_sha256 = Column(String(128), nullable=False)
    actor = Column(String(255), nullable=False)
    execution_audit_record_id = Column(
        Integer,
        ForeignKey("audit_logs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    result_envelope_sha256 = Column(String(128), nullable=False)


def decode_record_ids(value: str | None) -> dict[str, Any]:
    try:
        payload = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def result_row_snapshot(row: GovernanceExecutionResult) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "result_record_id": row.id,
        "execution_id": row.execution_id,
        "confirmation_sha256": row.confirmation_sha256,
        "confirmation_issue_audit_id": row.confirmation_issue_audit_id,
        "contract_validation_sha256": row.contract_validation_sha256,
        "case_id": row.case_id,
        "governance_action": row.governance_action,
        "delegate_service": row.delegate_service,
        "authoritative_record_ids": decode_record_ids(
            row.authoritative_record_ids
        ),
        "result_reference_sha256": row.result_reference_sha256,
        "final_state": row.final_state,
        "state_version": row.state_version,
        "workspace_sha256": row.workspace_sha256,
        "actor": row.actor,
        "execution_audit_record_id": row.execution_audit_record_id,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
        "result_envelope_sha256": row.result_envelope_sha256,
        "automatic_retry": False,
    }
