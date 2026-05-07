"""user status and stricter constraints

Revision ID: 0003_user_status_and_constraints
Revises: 0002_audit_logs_and_indexes
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_user_status_and_constraints"
down_revision = "0002_audit_logs_and_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_targets_created_at", "targets", ["created_at"])

    with op.batch_alter_table("targets") as batch:
        batch.alter_column("type", existing_type=sa.String(), nullable=False)
        batch.alter_column("value", existing_type=sa.String(), nullable=False)
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    with op.batch_alter_table("tools") as batch:
        batch.alter_column("name", existing_type=sa.String(), nullable=False)
    with op.batch_alter_table("users") as batch:
        batch.alter_column("username", existing_type=sa.String(), nullable=False)
        batch.alter_column("password_hash", existing_type=sa.String(), nullable=False)
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    with op.batch_alter_table("results") as batch:
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("tool_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("data", existing_type=sa.Text(), nullable=False)
        batch.alter_column(
            "timestamp", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    with op.batch_alter_table("profiles") as batch:
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("source", existing_type=sa.String(), nullable=False)
        batch.alter_column("raw", existing_type=sa.Text(), nullable=False)
        batch.alter_column("normalized", existing_type=sa.Text(), nullable=False)
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    with op.batch_alter_table("media") as batch:
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("source_url", existing_type=sa.String(), nullable=False)
        batch.alter_column("path", existing_type=sa.String(), nullable=False)
        batch.alter_column("checksum", existing_type=sa.String(), nullable=False)
        batch.alter_column("content_type", existing_type=sa.String(), nullable=False)
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )


def downgrade():
    with op.batch_alter_table("media") as batch:
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column("content_type", existing_type=sa.String(), nullable=True)
        batch.alter_column("checksum", existing_type=sa.String(), nullable=True)
        batch.alter_column("path", existing_type=sa.String(), nullable=True)
        batch.alter_column("source_url", existing_type=sa.String(), nullable=True)
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("profiles") as batch:
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column("normalized", existing_type=sa.Text(), nullable=True)
        batch.alter_column("raw", existing_type=sa.Text(), nullable=True)
        batch.alter_column("source", existing_type=sa.String(), nullable=True)
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("results") as batch:
        batch.alter_column(
            "timestamp", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column("data", existing_type=sa.Text(), nullable=True)
        batch.alter_column("tool_id", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("target_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("users") as batch:
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column("password_hash", existing_type=sa.String(), nullable=True)
        batch.alter_column("username", existing_type=sa.String(), nullable=True)
    with op.batch_alter_table("tools") as batch:
        batch.alter_column("name", existing_type=sa.String(), nullable=True)
    with op.batch_alter_table("targets") as batch:
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch.alter_column("value", existing_type=sa.String(), nullable=True)
        batch.alter_column("type", existing_type=sa.String(), nullable=True)

    op.drop_index("ix_targets_created_at", table_name="targets")
    op.drop_column("users", "is_active")
