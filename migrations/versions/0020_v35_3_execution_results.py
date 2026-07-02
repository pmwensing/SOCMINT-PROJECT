"""v35.3 authoritative governance execution result envelopes

Revision ID: 0020_v35_3_execution_results
Revises: 0019_v35_1_governance_executions
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0020_v35_3_execution_results"
down_revision = "0019_v35_1_governance_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governance_execution_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("confirmation_sha256", sa.String(length=128), nullable=False),
        sa.Column("confirmation_issue_audit_id", sa.Integer(), nullable=False),
        sa.Column("contract_validation_sha256", sa.String(length=128), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("governance_action", sa.String(length=128), nullable=False),
        sa.Column("delegate_service", sa.String(length=255), nullable=False),
        sa.Column("authoritative_record_ids", sa.Text(), nullable=False),
        sa.Column("result_reference_sha256", sa.String(length=128), nullable=False),
        sa.Column("final_state", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("workspace_sha256", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("execution_audit_record_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_envelope_sha256", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["governance_executions.execution_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "execution_id",
            name="uq_governance_execution_results_execution_id",
        ),
        sa.UniqueConstraint(
            "result_envelope_sha256",
            name="uq_governance_execution_results_envelope_sha256",
        ),
    )
    op.create_index(
        "ix_governance_execution_results_case_action",
        "governance_execution_results",
        ["case_id", "governance_action"],
        unique=False,
    )
    op.create_index(
        "ix_governance_execution_results_recorded_at",
        "governance_execution_results",
        ["recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_governance_execution_results_recorded_at",
        table_name="governance_execution_results",
    )
    op.drop_index(
        "ix_governance_execution_results_case_action",
        table_name="governance_execution_results",
    )
    op.drop_table("governance_execution_results")
