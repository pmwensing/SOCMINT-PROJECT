"""billing tables

Revision ID: 0011_billing
Revises: 0010_membership_quotas
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_billing"
down_revision = "0010_membership_quotas"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "billing_events"):
        op.create_table(
            "billing_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("provider_event_id", sa.String(length=255), nullable=False, unique=True),
            sa.Column("event_type", sa.String(length=128), nullable=False),
            sa.Column("username", sa.String(length=255), nullable=True),
            sa.Column("plan_key", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_billing_events_username", "billing_events", ["username"])
        op.create_index("ix_billing_events_type_created", "billing_events", ["event_type", "created_at"])

    if not has_table(bind, "checkout_sessions"):
        op.create_table(
            "checkout_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("checkout_id", sa.String(length=255), nullable=False, unique=True),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("plan_key", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("success_url", sa.Text(), nullable=True),
            sa.Column("cancel_url", sa.Text(), nullable=True),
            sa.Column("provider_payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_checkout_sessions_username", "checkout_sessions", ["username"])
        op.create_index("ix_checkout_sessions_plan_status", "checkout_sessions", ["plan_key", "status"])


def downgrade():
    bind = op.get_bind()
    for index_name, table_name in (
        ("ix_checkout_sessions_plan_status", "checkout_sessions"),
        ("ix_checkout_sessions_username", "checkout_sessions"),
        ("ix_billing_events_type_created", "billing_events"),
        ("ix_billing_events_username", "billing_events"),
    ):
        if has_table(bind, table_name):
            try:
                op.drop_index(index_name, table_name=table_name)
            except Exception:
                pass
    for table_name in ("checkout_sessions", "billing_events"):
        if has_table(bind, table_name):
            op.drop_table(table_name)
