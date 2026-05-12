"""billing customer links

Revision ID: 0013_billing_customer_links
Revises: 0012_tor_status
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_billing_customer_links"
down_revision = "0012_tor_status"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    return table_name in sa.inspect(bind).get_table_names()


def upgrade():
    bind = op.get_bind()
    if not has_table(bind, "billing_customer_links"):
        op.create_table(
            "billing_customer_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(length=255), nullable=False, unique=True),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("customer_id", sa.String(length=255), nullable=False),
            sa.Column("subscription_id", sa.String(length=255), nullable=True),
            sa.Column("plan_key", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_billing_customer_links_customer", "billing_customer_links", ["customer_id"])
        op.create_index("ix_billing_customer_links_subscription", "billing_customer_links", ["subscription_id"])


def downgrade():
    bind = op.get_bind()
    if has_table(bind, "billing_customer_links"):
        try:
            op.drop_index("ix_billing_customer_links_subscription", table_name="billing_customer_links")
            op.drop_index("ix_billing_customer_links_customer", table_name="billing_customer_links")
        except Exception:
            pass
        op.drop_table("billing_customer_links")
