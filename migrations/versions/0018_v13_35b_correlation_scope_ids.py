"""v13.35B persistent correlation scope ids

Revision ID: 0018_v13_35b_correlation_scope_ids
Revises: 0017_v12_10_schema_reconciliation
Create Date: 2026-06-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0018_v13_35b_correlation_scope_ids"
down_revision = "0017_v12_10_schema_reconciliation"
branch_labels = None
depends_on = None

TABLES = [
    "spine_seeds",
    "spine_connector_runs",
    "spine_observations",
    "spine_dossier_assertions",
    "media_profile_enrichments",
    "account_discoveries",
]


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    existing_tables = _tables()
    for table_name in TABLES:
        if table_name not in existing_tables:
            continue

        columns = _columns(table_name)
        if "correlation_scope_id" not in columns:
            op.add_column(table_name, sa.Column("correlation_scope_id", sa.String(length=80), nullable=True))
        if "correlation_scope_state" not in columns:
            op.add_column(table_name, sa.Column("correlation_scope_state", sa.String(length=40), nullable=True))
        if "correlation_scope_reason" not in columns:
            op.add_column(table_name, sa.Column("correlation_scope_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    existing_tables = _tables()
    for table_name in reversed(TABLES):
        if table_name not in existing_tables:
            continue

        columns = _columns(table_name)
        for column_name in [
            "correlation_scope_reason",
            "correlation_scope_state",
            "correlation_scope_id",
        ]:
            if column_name in columns:
                op.drop_column(table_name, column_name)
