"""case access tables

Revision ID: 0014_case_access
Revises: 0013_billing_customer_links
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_case_access"
down_revision = "0013_billing_customer_links"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    return table_name in sa.inspect(bind).get_table_names()


def upgrade():
    bind = op.get_bind()
    if not has_table(bind, "team_memberships"):
        op.create_table(
            "team_memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("team_key", sa.String(length=128), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("team_key", "username", name="uq_team_memberships_team_user"),
        )
    if not has_table(bind, "case_assignments"):
        op.create_table(
            "case_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("access_level", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("case_id", "username", name="uq_case_assignments_case_user"),
        )


def downgrade():
    bind = op.get_bind()
    if has_table(bind, "case_assignments"):
        op.drop_table("case_assignments")
    if has_table(bind, "team_memberships"):
        op.drop_table("team_memberships")
