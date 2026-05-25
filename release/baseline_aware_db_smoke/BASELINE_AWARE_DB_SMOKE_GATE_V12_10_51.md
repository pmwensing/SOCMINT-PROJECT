# v12.10.51 Baseline-Aware DB Smoke Gate

- **status**: `GO`
- **release_status**: `PASS GO`
- **schema_lock**: `BASELINE_AWARE_DB_SMOKE_GO`
- **schema_mutation**: `temp_sqlite_only`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **baseline_revision**: `0017_v12_10_schema_reconciliation`
- **head_revision**: `0018_approved_model_migration`
- **version_after_upgrade**: `0018_approved_model_migration`
- **version_after_downgrade**: `0017_v12_10_schema_reconciliation`
- **approved_table_count**: `18`
- **approved_baseline_table_count**: `16`
- **owned_0018_table_count**: `2`
- **missing_after_upgrade**: `0`
- **owned_lingering_after_downgrade**: `0`
- **baseline_missing_after_downgrade**: `0`

## True 0018-owned tables

- `identity_columns`
- `all_tab_identity_cols`

## Approved baseline tables allowed to remain after downgrade

- `connector_runs`
- `identity_edges`
- `identity_graphs`
- `identity_merge_candidates`
- `identity_nodes`
- `policy_gate_events`
- `retention_runs`
- `spine_connector_runs`
- `spine_contradictions`
- `spine_dossier_assertions`
- `spine_observations`
- `spine_raw_artifacts`
- `spine_seeds`
- `spine_subjects`
- `spine_validation_events`
- `workbench_jobs`

## Errors

- none