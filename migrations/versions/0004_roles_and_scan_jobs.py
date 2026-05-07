"""roles and scan jobs

Revision ID: 0004_roles_and_scan_jobs
Revises: 0003_user_status_and_constraints
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_roles_and_scan_jobs"
down_revision = "0003_user_status_and_constraints"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=False, server_default="viewer"),
    )
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = true")

    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_value", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("tools", sa.Text(), nullable=False),
        sa.Column("enrich", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("requested_by", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "target_id", sa.Integer(), sa.ForeignKey("targets.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_scan_jobs_status_created_at",
        "scan_jobs",
        ["status", "created_at"],
    )


def downgrade():
    op.drop_index("ix_scan_jobs_status_created_at", table_name="scan_jobs")
    op.drop_table("scan_jobs")
    op.drop_column("users", "role")
