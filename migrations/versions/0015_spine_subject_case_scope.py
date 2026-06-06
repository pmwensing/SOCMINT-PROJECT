"""spine subject case scope

Revision ID: 0015_spine_subject_case_scope
Revises: 0014_case_access
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_spine_subject_case_scope"
down_revision = "0014_case_access"
branch_labels = None
depends_on = None


def has_column(bind, table_name, column_name):
    columns = sa.inspect(bind).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def has_index(bind, table_name, index_name):
    indexes = sa.inspect(bind).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade():
    bind = op.get_bind()
    if not has_column(bind, "spine_subjects", "case_key"):
        op.add_column("spine_subjects", sa.Column("case_key", sa.String(length=128), nullable=True))
    if not has_index(bind, "spine_subjects", "ix_spine_subjects_case_key"):
        op.create_index("ix_spine_subjects_case_key", "spine_subjects", ["case_key"])


def downgrade():
    bind = op.get_bind()
    if has_index(bind, "spine_subjects", "ix_spine_subjects_case_key"):
        op.drop_index("ix_spine_subjects_case_key", table_name="spine_subjects")
    if has_column(bind, "spine_subjects", "case_key"):
        op.drop_column("spine_subjects", "case_key")
