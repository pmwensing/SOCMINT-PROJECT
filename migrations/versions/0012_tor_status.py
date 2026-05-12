"""tor status table

Revision ID: 0012_tor_status
Revises: 0011_billing
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_tor_status"
down_revision = "0011_billing"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    if not has_table(bind, "hidden_service_status"):
        op.create_table(
            "hidden_service_status",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("service_name", sa.String(length=128), nullable=False, unique=True),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("onion_hostname", sa.String(length=255), nullable=True),
            sa.Column("service_dir", sa.Text(), nullable=False),
            sa.Column("tor_port", sa.Integer(), nullable=False),
            sa.Column("target_host", sa.String(length=255), nullable=False),
            sa.Column("target_port", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("last_check_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    if has_table(bind, "hidden_service_status"):
        op.drop_table("hidden_service_status")
