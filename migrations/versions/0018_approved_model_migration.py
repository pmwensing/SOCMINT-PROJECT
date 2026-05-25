"""v12.10.37 APPROVED MODEL MIGRATION

Promoted into alembic/versions by v12.10.37 promotion gate.
This migration is not applied automatically by this promotion gate.
None comments preserved for final schema review.  # TODO: executable placeholder replaced with safe default; review

Revision ID: 0018_approved_model_migration
Revises: 0017_v12_10_schema_reconciliation
"""

# PROMOTED MIGRATION FILE — DO NOT UPGRADE WITHOUT FINAL DB SMOKE TEST.
# Promoted by v12.10.37. No alembic upgrade was run by this build.

from alembic import op
import sqlalchemy as sa

revision = "0018_approved_model_migration"
down_revision = "0017_v12_10_schema_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    # --- approved table: spine_connector_runs ---
    # classification: PASS
    # priority: P0
    # domain: connectors
    # op.create_table(  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_connector_runs",  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("connector_key", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("seed_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("status", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("raw_result_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_dossier_assertions ---
    # classification: PASS
    # priority: P0
    # domain: dossier
    # op.create_table(  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_dossier_assertions",  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("assertion_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("confidence", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("validation_state", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_dossier_assertions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_raw_artifacts ---
    # classification: PASS
    # priority: P0
    # domain: evidence
    # op.create_table(  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_raw_artifacts",  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("run_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("kind", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("path", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("sha256", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("mime_type", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("size_bytes", sa.Integer()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("meta_json", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_raw_artifacts` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_observations ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_observations",  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("run_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("observation_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("confidence", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("source_ref", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("evidence_ref", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_observations` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_seeds ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_seeds",  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("seed_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("raw_value", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("normalized_value", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("pii_hash", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_seeds` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_subjects ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_subjects",  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("label", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_subjects` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_validation_events ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_validation_events",  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("assertion_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("action", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_validation_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: retention_runs ---
    # classification: PASS
    # priority: P0
    # domain: connectors
    # op.create_table(  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "retention_runs",  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("mode", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("status", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("result_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `retention_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: workbench_jobs ---
    # classification: PASS
    # priority: P0
    # domain: connectors
    # op.create_table(  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "workbench_jobs",  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("job_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("status", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("priority", sa.Integer(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("attempts", sa.Integer(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("result_json", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("error", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("started_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("finished_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `workbench_jobs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: identity_columns ---
    # classification: PASS
    # priority: P0
    # domain: identity
    op.create_table(
        "identity_columns",
        sa.Column("object_id", sa.Integer()),  # TODO: confirm type/nullability/default
        sa.Column("name", sa.String()),  # TODO: confirm type
        sa.Column("column_id", sa.Integer()),  # TODO: confirm type/nullability/default
        sa.Column("is_identity", sa.Boolean()),  # TODO: confirm type/nullability/default
        sa.Column("seed_value", sa.Numeric()),  # TODO: confirm precision/scale
        sa.Column("increment_value", sa.Numeric()),  # TODO: confirm precision/scale
        sa.Column("last_value", sa.Numeric()),  # TODO: confirm precision/scale
        sa.Column("is_not_for_replication", sa.Boolean()),  # TODO: confirm type/nullability/default
    )

    # --- approved table: identity_edges ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "identity_edges",  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("from_node_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("to_node_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("edge_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("confidence", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("evidence_ref", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("validation_state", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `identity_edges` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: identity_graphs ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "identity_graphs",  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("label", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `identity_graphs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: identity_merge_candidates ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "identity_merge_candidates",  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("entity_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("normalized_value", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("node_ids_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("confidence", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("state", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("reason", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `identity_merge_candidates` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: identity_nodes ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "identity_nodes",  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("entity_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("normalized_value", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("display_value", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("confidence", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("validation_state", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `identity_nodes` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: spine_contradictions ---
    # classification: PASS
    # priority: P0
    # domain: identity
    # op.create_table(  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "spine_contradictions",  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("conflict_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("severity", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("status", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("assertion_ids_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("summary", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `spine_contradictions` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: policy_gate_events ---
    # classification: PASS
    # priority: P0
    # domain: policy
    # op.create_table(  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "policy_gate_events",  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("action", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("allowed", sa.Integer(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("reasons_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("payload_json", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("actor", sa.String(length=255)),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `policy_gate_events` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: connector_runs ---
    # classification: PASS
    # priority: P1
    # domain: connectors
    # op.create_table(  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # "connector_runs",  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("id", sa.Integer(), primary_key=True),  # TODO: confirm primary key  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("target_id", sa.Integer()),  # TODO: confirm FK target and migration order  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("target_value", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("target_type", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("connector", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("status", sa.String(length=255), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("command", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("raw_result", sa.Text(), nullable=False),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("error", sa.Text()),  # TODO: confirm type/nullability/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
        # sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership
    # )  # TODO: create_table neutralized: `connector_runs` already exists at 0017_v12_10_schema_reconciliation; review original schema ownership

    # --- approved table: all_tab_identity_cols ---
    # classification: PASS
    # priority: P1
    # domain: identity
    op.create_table(
        "all_tab_identity_cols",
        sa.Column("owner", sa.String()),  # TODO: confirm type
        sa.Column("mview_name", sa.String()),  # TODO: confirm type
        sa.Column("container_name", sa.String()),  # TODO: confirm type
        sa.Column("query", sa.String()),  # TODO: confirm type
        sa.Column("query_len", sa.String()),  # TODO: confirm type
        sa.Column("updatable", sa.String()),  # TODO: confirm type
        sa.Column("update_log", sa.String()),  # TODO: confirm type
        sa.Column("master_rollback_seg", sa.String()),  # TODO: confirm type
        sa.Column("master_link", sa.String()),  # TODO: confirm type
        sa.Column("rewrite_enabled", sa.String()),  # TODO: confirm type
        sa.Column("rewrite_capability", sa.String()),  # TODO: confirm type
        sa.Column("refresh_mode", sa.String()),  # TODO: confirm type
        sa.Column("refresh_method", sa.String()),  # TODO: confirm type
        sa.Column("build_mode", sa.String()),  # TODO: confirm type
        sa.Column("fast_refreshable", sa.String()),  # TODO: confirm type
        sa.Column("last_refresh_type", sa.String()),  # TODO: confirm type
        sa.Column("last_refresh_date", sa.Date()),  # TODO: confirm type/nullability/default
        sa.Column("last_refresh_end_time", sa.Date()),  # TODO: confirm type/nullability/default
        sa.Column("staleness", sa.String()),  # TODO: confirm type
        sa.Column("after_fast_refresh", sa.String()),  # TODO: confirm type
        sa.Column("unknown_prebuilt", sa.String()),  # TODO: confirm type
        sa.Column("unknown_plsql_func", sa.String()),  # TODO: confirm type
        sa.Column("unknown_external_table", sa.String()),  # TODO: confirm type
        sa.Column("unknown_consider_fresh", sa.String()),  # TODO: confirm type
        sa.Column("unknown_import", sa.String()),  # TODO: confirm type
        sa.Column("unknown_trusted_fd", sa.String()),  # TODO: confirm type
        sa.Column("compile_state", sa.String()),  # TODO: confirm type
        sa.Column("use_no_index", sa.String()),  # TODO: confirm type
        sa.Column("stale_since", sa.Date()),  # TODO: confirm type/nullability/default
        sa.Column("num_pct_tables", sa.String()),  # TODO: confirm type
        sa.Column("num_fresh_pct_regions", sa.String()),  # TODO: confirm type
        sa.Column("num_stale_pct_regions", sa.String()),  # TODO: confirm type
        sa.Column("segment_created", sa.String()),  # TODO: confirm type
        sa.Column("evaluation_edition", sa.String()),  # TODO: confirm type
        sa.Column("unusable_before", sa.String()),  # TODO: confirm type
        sa.Column("unusable_beginning", sa.String()),  # TODO: confirm type
        sa.Column("default_collation", sa.String()),  # TODO: confirm type
        sa.Column("on_query_computation", sa.String()),  # TODO: confirm type
        sa.Column("auto", sa.String()),  # TODO: confirm type
        sa.Column("table_name", sa.String()),  # TODO: confirm type
        sa.Column("column_name", sa.String()),  # TODO: confirm type
        sa.Column("generation_type", sa.String()),  # TODO: confirm type
        sa.Column("sequence_name", sa.String()),  # TODO: confirm type
        sa.Column("identity_options", sa.String()),  # TODO: confirm type
        sa.Column("data_type", sa.String()),  # TODO: confirm type
        sa.Column("data_type_mod", sa.String()),  # TODO: confirm type
        sa.Column("data_type_owner", sa.String()),  # TODO: confirm type
        sa.Column("data_length", sa.String()),  # TODO: confirm type
        sa.Column("data_precision", sa.String()),  # TODO: confirm type
        sa.Column("data_scale", sa.String()),  # TODO: confirm type
        sa.Column("nullable", sa.String()),  # TODO: confirm type
        sa.Column("column_id", sa.String()),  # TODO: confirm type
        sa.Column("default_length", sa.String()),  # TODO: confirm type
        sa.Column("data_default", sa.String()),  # TODO: confirm type
        sa.Column("num_distinct", sa.String()),  # TODO: confirm type
        sa.Column("low_value", sa.String()),  # TODO: confirm type
        sa.Column("high_value", sa.String()),  # TODO: confirm type
        sa.Column("density", sa.String()),  # TODO: confirm type
        sa.Column("num_nulls", sa.String()),  # TODO: confirm type
        sa.Column("num_buckets", sa.String()),  # TODO: confirm type
        sa.Column("last_analyzed", sa.Date()),  # TODO: confirm type/nullability/default
        sa.Column("sample_size", sa.String()),  # TODO: confirm type
        sa.Column("character_set_name", sa.String()),  # TODO: confirm type
        sa.Column("char_col_decl_length", sa.String()),  # TODO: confirm type
        sa.Column("global_stats", sa.String()),  # TODO: confirm type
        sa.Column("user_stats", sa.String()),  # TODO: confirm type
        sa.Column("avg_col_len", sa.String()),  # TODO: confirm type
        sa.Column("char_length", sa.String()),  # TODO: confirm type
        sa.Column("char_used", sa.String()),  # TODO: confirm type
        sa.Column("v80_fmt_image", sa.String()),  # TODO: confirm type
        sa.Column("data_upgraded", sa.String()),  # TODO: confirm type
        sa.Column("hidden_column", sa.String()),  # TODO: confirm type
        sa.Column("virtual_column", sa.String()),  # TODO: confirm type
    )


def downgrade():
    # Reverse dependency order.
    op.drop_table("all_tab_identity_cols")
    # op.drop_table("connector_runs")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("policy_gate_events")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_contradictions")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("identity_nodes")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("identity_merge_candidates")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("identity_graphs")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("identity_edges")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    op.drop_table("identity_columns")
    # op.drop_table("workbench_jobs")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("retention_runs")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_validation_events")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_subjects")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_seeds")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_observations")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_raw_artifacts")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_dossier_assertions")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
    # op.drop_table("spine_connector_runs")  # TODO: collision table existed before 0018; downgrade must not drop baseline table
