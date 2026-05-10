"""v7.1 model sync

Revision ID: 0005_v7_1_model_sync
Revises: 0004_roles_and_scan_jobs
Create Date: 2026-05-09
"""

from alembic import op

from src.socmint import database as db

revision = "0005_v7_1_model_sync"
down_revision = "0004_roles_and_scan_jobs"
branch_labels = None
depends_on = None


TABLE_NAMES = (
    "connector_runs",
    "findings",
    "spine_subjects",
    "spine_seeds",
    "spine_connector_runs",
    "spine_raw_artifacts",
    "spine_observations",
    "spine_dossier_assertions",
    "spine_validation_events",
    "identity_graphs",
    "identity_nodes",
    "identity_edges",
    "identity_merge_candidates",
    "media_profile_enrichments",
    "spine_contradictions",
    "dossier_exports",
    "workbench_jobs",
    "policy_gate_events",
    "retention_runs",
)


def _tables():
    return [db.Base.metadata.tables[name] for name in TABLE_NAMES]


def upgrade():
    db.Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade():
    db.Base.metadata.drop_all(bind=op.get_bind(), tables=reversed(_tables()))
