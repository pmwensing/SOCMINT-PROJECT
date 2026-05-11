"""high-end SOCMINT workflow tables

Revision ID: 0008_high_end_socmint_workflows
Revises: 0007_v7_2_2_review_decision_audit
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_high_end_socmint_workflows"
down_revision = "0007_v7_2_2_review_decision_audit"
branch_labels = None
depends_on = None


def has_table(bind, table_name):
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    if not has_table(bind, "case_records"):
        op.create_table(
            "case_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_key", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("priority", sa.String(length=64), nullable=False),
            sa.Column("review_state", sa.String(length=64), nullable=False),
            sa.Column("due_at", sa.String(length=64), nullable=True),
            sa.Column("tags_json", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_case_records_case_key", "case_records", ["case_key"], unique=True)
        op.create_index("ix_case_records_status", "case_records", ["status"])
        op.create_index("ix_case_records_priority", "case_records", ["priority"])
        op.create_index("ix_case_records_review_state", "case_records", ["review_state"])

    if not has_table(bind, "case_events"):
        op.create_table(
            "case_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("case_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("assignee", sa.String(length=255), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["case_id"], ["case_records.id"]),
        )
        op.create_index("ix_case_events_case_id", "case_events", ["case_id"])
        op.create_index("ix_case_events_event_type", "case_events", ["event_type"])
        op.create_index("ix_case_events_subject_id", "case_events", ["subject_id"])

    if not has_table(bind, "evidence_captures"):
        op.create_table(
            "evidence_captures",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capture_id", sa.String(length=64), nullable=False),
            sa.Column("url", sa.Text(), nullable=False),
            sa.Column("case_key", sa.String(length=128), nullable=True),
            sa.Column("subject_id", sa.Integer(), nullable=True),
            sa.Column("artifact_type", sa.String(length=64), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("headers_json", sa.Text(), nullable=False),
            sa.Column("cookies_json", sa.Text(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_evidence_captures_capture_id", "evidence_captures", ["capture_id"], unique=True)
        op.create_index("ix_evidence_captures_case_key", "evidence_captures", ["case_key"])
        op.create_index("ix_evidence_captures_subject_id", "evidence_captures", ["subject_id"])
        op.create_index("ix_evidence_captures_sha256", "evidence_captures", ["sha256"])

    if not has_table(bind, "responsible_use_scope"):
        op.create_table(
            "responsible_use_scope",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("updated_by", sa.String(length=255), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_responsible_use_scope_name", "responsible_use_scope", ["name"], unique=True)


def downgrade():
    bind = op.get_bind()
    for table in (
        "responsible_use_scope",
        "evidence_captures",
        "case_events",
        "case_records",
    ):
        if has_table(bind, table):
            op.drop_table(table)
