"""v7.2.1 review decision persistence

Revision ID: 0006_v7_2_1_review_decisions
Revises: 0005_v7_1_model_sync
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_v7_2_1_review_decisions"
down_revision = "0005_v7_1_model_sync"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def has_column(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "review_decisions"):
        op.create_table(
            "review_decisions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("item_id", sa.String(length=512), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=True),
            sa.Column("source_table", sa.String(length=128), nullable=False),
            sa.Column("source_id", sa.String(length=128), nullable=True),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="needs_review",
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("reviewer", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_review_decisions_item_id",
            "review_decisions",
            ["item_id"],
        )
        op.create_index(
            "ix_review_decisions_subject_id",
            "review_decisions",
            ["subject_id"],
        )
        op.create_index(
            "ix_review_decisions_source_table",
            "review_decisions",
            ["source_table"],
        )
        op.create_index(
            "ix_review_decisions_source_id",
            "review_decisions",
            ["source_id"],
        )
        op.create_index(
            "ix_review_decisions_status",
            "review_decisions",
            ["status"],
        )

    for table_name in ("spine_observations", "findings"):
        if has_table(bind, table_name):
            if not has_column(bind, table_name, "review_status"):
                op.add_column(
                    table_name,
                    sa.Column("review_status", sa.String(length=32), nullable=True),
                )
            if not has_column(bind, table_name, "review_note"):
                op.add_column(
                    table_name,
                    sa.Column("review_note", sa.Text(), nullable=True),
                )
            if not has_column(bind, table_name, "reviewed_at"):
                op.add_column(
                    table_name,
                    sa.Column("reviewed_at", sa.DateTime(), nullable=True),
                )


def downgrade():
    bind = op.get_bind()

    for table_name in ("spine_observations", "findings"):
        if has_table(bind, table_name):
            if has_column(bind, table_name, "reviewed_at"):
                op.drop_column(table_name, "reviewed_at")
            if has_column(bind, table_name, "review_note"):
                op.drop_column(table_name, "review_note")
            if has_column(bind, table_name, "review_status"):
                op.drop_column(table_name, "review_status")

    if has_table(bind, "review_decisions"):
        op.drop_index("ix_review_decisions_status", table_name="review_decisions")
        op.drop_index("ix_review_decisions_source_id", table_name="review_decisions")
        op.drop_index(
            "ix_review_decisions_source_table",
            table_name="review_decisions",
        )
        op.drop_index("ix_review_decisions_subject_id", table_name="review_decisions")
        op.drop_index("ix_review_decisions_item_id", table_name="review_decisions")
        op.drop_table("review_decisions")
