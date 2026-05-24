"""v12.10.30 schema reconciliation command-center tables

Revision ID: 0017_v12_10_schema_reconciliation
Revises: 0014_case_access
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_v12_10_schema_reconciliation"
down_revision = "0014_case_access"
branch_labels = None
depends_on = None


def _create_if_missing(name, *cols):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if name not in inspector.get_table_names():
        op.create_table(name, *cols)


def _drop_if_exists(name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if name in inspector.get_table_names():
        op.drop_table(name)


def upgrade():
    _create_if_missing(
        "dossier_exports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("run_id", sa.String(128), index=True, nullable=False),
        sa.Column("export_type", sa.String(64), nullable=False),
        sa.Column("path", sa.Text),
        sa.Column("sha256", sa.String(64)),
        sa.Column("manifest_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create_if_missing(
        "evidence_hash_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("artifact_id", sa.String(128), index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("stored_sha256", sa.String(64)),
        sa.Column("current_sha256", sa.String(64)),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create_if_missing(
        "intel_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("run_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), default="queued"),
        sa.Column("payload_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create_if_missing(
        "analyst_decisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("target_id", sa.String(128), index=True, nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create_if_missing(
        "strategic_risk_scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(64), nullable=False),
        sa.Column("details_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    _create_if_missing(
        "continuous_monitoring_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(128), index=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("target", sa.Text),
        sa.Column("status", sa.String(64), default="pending_review"),
        sa.Column("payload_json", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    for table in [
        "continuous_monitoring_events",
        "strategic_risk_scores",
        "analyst_decisions",
        "intel_runs",
        "evidence_hash_events",
        "dossier_exports",
    ]:
        _drop_if_exists(table)
