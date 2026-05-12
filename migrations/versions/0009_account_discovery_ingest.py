"""account discovery ingest table

Revision ID: 0009_account_discovery_ingest
Revises: 0008_high_end_socmint_workflows
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_account_discovery_ingest"
down_revision = "0008_high_end_socmint_workflows"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "account_discoveries"):
        op.create_table(
            "account_discoveries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("observation_id", sa.Integer(), nullable=False),
            sa.Column("assertion_id", sa.Integer(), nullable=True),
            sa.Column("discovery_type", sa.String(), nullable=False),
            sa.Column("platform", sa.String(), nullable=True),
            sa.Column("account_value", sa.Text(), nullable=False),
            sa.Column("profile_url", sa.Text(), nullable=True),
            sa.Column("confidence", sa.String(), nullable=False),
            sa.Column("review_state", sa.String(), nullable=False),
            sa.Column("capture_ids_json", sa.Text(), nullable=False),
            sa.Column("promoted_seed_id", sa.Integer(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["subject_id"], ["spine_subjects.id"]),
            sa.ForeignKeyConstraint(["observation_id"], ["spine_observations.id"]),
            sa.ForeignKeyConstraint(
                ["assertion_id"],
                ["spine_dossier_assertions.id"],
            ),
            sa.ForeignKeyConstraint(["promoted_seed_id"], ["spine_seeds.id"]),
        )
        op.create_index(
            "ix_account_discoveries_subject_id",
            "account_discoveries",
            ["subject_id"],
        )
        op.create_index(
            "ix_account_discoveries_observation_id",
            "account_discoveries",
            ["observation_id"],
            unique=True,
        )
        op.create_index(
            "ix_account_discoveries_review_state",
            "account_discoveries",
            ["review_state"],
        )
        op.create_index(
            "ix_account_discoveries_profile_url",
            "account_discoveries",
            ["profile_url"],
        )


def downgrade():
    bind = op.get_bind()
    if has_table(bind, "account_discoveries"):
        op.drop_index(
            "ix_account_discoveries_profile_url",
            table_name="account_discoveries",
        )
        op.drop_index(
            "ix_account_discoveries_review_state",
            table_name="account_discoveries",
        )
        op.drop_index(
            "ix_account_discoveries_observation_id",
            table_name="account_discoveries",
        )
        op.drop_index(
            "ix_account_discoveries_subject_id",
            table_name="account_discoveries",
        )
        op.drop_table("account_discoveries")
