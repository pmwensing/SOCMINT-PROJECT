"""v35.1 authoritative governance execution state

Revision ID: 0019_v35_1_governance_executions
Revises: 0018_v13_35b_correlation_scope_ids
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0019_v35_1_governance_executions"
down_revision = "0018_v13_35b_correlation_scope_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governance_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("execution_id", sa.String(length=64), nullable=False),
        sa.Column("confirmation_sha256", sa.String(length=128), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("governance_action", sa.String(length=128), nullable=False),
        sa.Column("delegate_service", sa.String(length=255), nullable=False),
        sa.Column("current_state", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_actor", sa.String(length=255), nullable=False),
        sa.Column("last_reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "execution_id", name="uq_governance_executions_execution_id"
        ),
        sa.UniqueConstraint(
            "confirmation_sha256",
            name="uq_governance_executions_confirmation_sha256",
        ),
    )
    op.create_index(
        "ix_governance_executions_case_state",
        "governance_executions",
        ["case_id", "current_state"],
        unique=False,
    )
    op.create_index(
        "ix_governance_executions_updated_at",
        "governance_executions",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_governance_executions_updated_at",
        table_name="governance_executions",
    )
    op.drop_index(
        "ix_governance_executions_case_state",
        table_name="governance_executions",
    )
    op.drop_table("governance_executions")
