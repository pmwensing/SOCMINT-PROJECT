"""membership and quota tables

Revision ID: 0010_membership_quotas
Revises: 0009_account_discovery_ingest
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_membership_quotas"
down_revision = "0009_account_discovery_ingest"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "membership_plans"):
        op.create_table(
            "membership_plans",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plan_key", sa.String(length=64), nullable=False, unique=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("price_label", sa.String(length=64), nullable=False),
            sa.Column("entitlements_json", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not has_table(bind, "user_memberships"):
        op.create_table(
            "user_memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("plan_key", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("period_started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_ends_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
            sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["plan_key"], ["membership_plans.plan_key"]),
            sa.UniqueConstraint("user_id", name="uq_user_memberships_user_id"),
        )
        op.create_index("ix_user_memberships_plan_key", "user_memberships", ["plan_key"])
        op.create_index("ix_user_memberships_status", "user_memberships", ["status"])

    if not has_table(bind, "usage_events"):
        op.create_table(
            "usage_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("quota_key", sa.String(length=128), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_usage_events_user_action_created", "usage_events", ["user_id", "action", "created_at"])
        op.create_index("ix_usage_events_quota_created", "usage_events", ["quota_key", "created_at"])

    if not has_table(bind, "usage_counters"):
        op.create_table(
            "usage_counters",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("quota_key", sa.String(length=128), nullable=False),
            sa.Column("period_key", sa.String(length=64), nullable=False),
            sa.Column("used", sa.Integer(), nullable=False),
            sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint("user_id", "quota_key", "period_key", name="uq_usage_counters_user_quota_period"),
        )
        op.create_index("ix_usage_counters_user_quota", "usage_counters", ["user_id", "quota_key"])

    if not has_table(bind, "quota_overrides"):
        op.create_table(
            "quota_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("quota_key", sa.String(length=128), nullable=False),
            sa.Column("limit_value", sa.Integer(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_quota_overrides_user_quota", "quota_overrides", ["user_id", "quota_key"])


def downgrade():
    bind = op.get_bind()
    for index_name, table_name in (
        ("ix_quota_overrides_user_quota", "quota_overrides"),
        ("ix_usage_counters_user_quota", "usage_counters"),
        ("ix_usage_events_quota_created", "usage_events"),
        ("ix_usage_events_user_action_created", "usage_events"),
        ("ix_user_memberships_status", "user_memberships"),
        ("ix_user_memberships_plan_key", "user_memberships"),
    ):
        if has_table(bind, table_name):
            try:
                op.drop_index(index_name, table_name=table_name)
            except Exception:
                pass
    for table_name in ("quota_overrides", "usage_counters", "usage_events", "user_memberships", "membership_plans"):
        if has_table(bind, table_name):
            op.drop_table(table_name)
