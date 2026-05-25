"""NON-EXECUTABLE REVIEW DRAFT — v12.10.33

This file is intentionally generated outside alembic/versions.
Do not copy into alembic/versions until each table/column is reviewed.

Revision ID: 0018_REVIEW_ONLY_p0_p1_candidate_tables
Revises: 0017_v12_10_schema_reconciliation
"""

# REVIEW ONLY — NOT A REAL MIGRATION
# Schema mutation: none

from alembic import op
import sqlalchemy as sa

revision = "0018_REVIEW_ONLY_p0_p1_candidate_tables"
down_revision = "0017_v12_10_schema_reconciliation"
branch_labels = None
depends_on = None

def upgrade():
    raise RuntimeError("NON-EXECUTABLE REVIEW DRAFT: do not run")

    # Candidate: spine_connector_runs (P0 / PASS)
    # domain: connectors
    # status: active_candidate
    # op.create_table(
    #     "spine_connector_runs",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("connector_key", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("seed_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("raw_result_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_dossier_assertions (P0 / PASS)
    # domain: dossier
    # status: active_candidate
    # op.create_table(
    #     "spine_dossier_assertions",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("assertion_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("confidence", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("validation_state", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_raw_artifacts (P0 / PASS)
    # domain: evidence
    # status: active_candidate
    # op.create_table(
    #     "spine_raw_artifacts",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("run_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("kind", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("path", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("sha256", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("mime_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("size_bytes", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("meta_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_observations (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "spine_observations",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("run_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("observation_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("confidence", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("source_ref", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("evidence_ref", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_seeds (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "spine_seeds",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("seed_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("raw_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("pii_hash", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_subjects (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "spine_subjects",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("label", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_validation_events (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "spine_validation_events",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("assertion_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("action", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: retention_runs (P0 / PASS)
    # domain: connectors
    # status: active_candidate
    # op.create_table(
    #     "retention_runs",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("mode", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("result_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: workbench_jobs (P0 / PASS)
    # domain: connectors
    # status: active_candidate
    # op.create_table(
    #     "workbench_jobs",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("job_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("priority", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("attempts", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("result_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("error", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("started_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("finished_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: identity_columns (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "identity_columns",
    #     sa.Column("object_id", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("column_id", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("is_identity", sa.Boolean()),  # TODO: confirm type/nullability/default
    #     sa.Column("seed_value", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("increment_value", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("last_value", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("is_not_for_replication", sa.Boolean()),  # TODO: confirm type/nullability/default
    # )

    # Candidate: identity_edges (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "identity_edges",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("from_node_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("to_node_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("edge_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("confidence", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("evidence_ref", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("validation_state", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: identity_graphs (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "identity_graphs",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("label", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: identity_merge_candidates (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "identity_merge_candidates",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("entity_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("node_ids_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("confidence", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("state", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("reason", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: identity_nodes (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "identity_nodes",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("graph_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("entity_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("normalized_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("display_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("confidence", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("validation_state", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: spine_contradictions (P0 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "spine_contradictions",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("conflict_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("severity", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("assertion_ids_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("summary", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("note", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    #     sa.Column("updated_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: policy_gate_events (P0 / PASS)
    # domain: policy
    # status: active_candidate
    # op.create_table(
    #     "policy_gate_events",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("action", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("allowed", sa.Integer()),  # TODO: confirm type/nullability/default
    #     sa.Column("reasons_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("actor", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: connector_runs (P1 / PASS)
    # domain: connectors
    # status: active_candidate
    # op.create_table(
    #     "connector_runs",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("target_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("target_value", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("target_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("connector", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("command", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("raw_result", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("error", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: all_tab_identity_cols (P1 / PASS)
    # domain: identity
    # status: active_candidate
    # op.create_table(
    #     "all_tab_identity_cols",
    #     sa.Column("owner", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("mview_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("container_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("query", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("query_len", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("updatable", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("update_log", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("master_rollback_seg", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("master_link", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("rewrite_enabled", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("rewrite_capability", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("refresh_mode", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("refresh_method", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("build_mode", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("fast_refreshable", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("last_refresh_type", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("last_refresh_date", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("last_refresh_end_time", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("staleness", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("after_fast_refresh", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_prebuilt", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_plsql_func", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_external_table", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_consider_fresh", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_import", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unknown_trusted_fd", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("compile_state", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("use_no_index", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("stale_since", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_pct_tables", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_fresh_pct_regions", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_stale_pct_regions", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("segment_created", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("evaluation_edition", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unusable_before", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("unusable_beginning", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("default_collation", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("on_query_computation", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("auto", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("table_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("column_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("generation_type", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("sequence_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("identity_options", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_type", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_type_mod", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_type_owner", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_length", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_precision", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_scale", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("nullable", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("column_id", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("default_length", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_default", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_distinct", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("low_value", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("high_value", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("density", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_nulls", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("num_buckets", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("last_analyzed", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("sample_size", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("character_set_name", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("char_col_decl_length", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("global_stats", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("user_stats", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("avg_col_len", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("char_length", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("char_used", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("v80_fmt_image", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("data_upgraded", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("hidden_column", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    #     sa.Column("virtual_column", sa.String()  # TODO confirm type),  # TODO: confirm type/nullability/default
    # )

    # Candidate: media_profile_enrichments (P1 / PASS_WITH_REVIEW_NOTES)
    # domain: connectors
    # status: active_candidate
    # op.create_table(
    #     "media_profile_enrichments",
    #     sa.Column("id", sa.Integer()),  # TODO: confirm primary key
    #     sa.Column("subject_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("observation_id", sa.Integer()),  # TODO: confirm FK target and migration order
    #     sa.Column("enrichment_type", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("status", sa.String(length=TODO)),  # TODO: confirm type/nullability/default
    #     sa.Column("source_value", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("artifact_ref", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("payload_json", sa.Text()),  # TODO: confirm type/nullability/default
    #     sa.Column("created_at", sa.DateTime(timezone=True)),  # TODO: confirm timezone/default
    # )

    # Candidate: employee (P1 / REVIEW)
    # domain: uncategorized
    # status: active_candidate
    # op.create_table(
    #     "employee",
    #     # TODO: no columns extracted; review source manually
    # )


def downgrade():
    raise RuntimeError("NON-EXECUTABLE REVIEW DRAFT: do not run")