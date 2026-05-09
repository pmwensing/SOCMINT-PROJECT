"""v7.2.2 review decision audit trail and bulk actions

Revision ID: 0007_v7_2_2_review_decision_audit
Revises: 0006_v7_2_1_review_decisions
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_v7_2_2_review_decision_audit"
down_revision = "0006_v7_2_1_review_decisions"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "review_decision_audit"):
        op.create_table(
            "review_decision_audit",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("decision_id", sa.Integer(), nullable=True),
            sa.Column("item_id", sa.String(length=512), nullable=False),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("old_status", sa.String(length=32), nullable=True),
            sa.Column("new_status", sa.String(length=32), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("reviewer", sa.String(length=255), nullable=True),
            sa.Column("batch_id", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_review_decision_audit_decision_id",
            "review_decision_audit",
            ["decision_id"],
        )
        op.create_index(
            "ix_review_decision_audit_item_id",
            "review_decision_audit",
            ["item_id"],
        )
        op.create_index(
            "ix_review_decision_audit_action",
            "review_decision_audit",
            ["action"],
        )
        op.create_index(
            "ix_review_decision_audit_new_status",
            "review_decision_audit",
            ["new_status"],
        )
        op.create_index(
            "ix_review_decision_audit_batch_id",
            "review_decision_audit",
            ["batch_id"],
        )


def downgrade():
    bind = op.get_bind()

    if has_table(bind, "review_decision_audit"):
        op.drop_index(
            "ix_review_decision_audit_batch_id",
            table_name="review_decision_audit",
        )
        op.drop_index(
            "ix_review_decision_audit_new_status",
            table_name="review_decision_audit",
        )
        op.drop_index(
            "ix_review_decision_audit_action",
            table_name="review_decision_audit",
        )
        op.drop_index(
            "ix_review_decision_audit_item_id",
            table_name="review_decision_audit",
        )
        op.drop_index(
            "ix_review_decision_audit_decision_id",
            table_name="review_decision_audit",
        )
        op.drop_table("review_decision_audit")
