# v12.10.42 DB Smoke Exact Failure Locator

- **smoke_status**: `NO-GO`
- **schema_mutation**: `none`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **version_after_upgrade**: `0017_v12_10_schema_reconciliation`
- **approved_table_count**: `18`
- **created_approved_table_count**: `16`
- **not_created_approved_table_count**: `2`
- **probable_failing_table**: `identity_columns`
- **failing_upgrade_output_path**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/db_smoke_exact_failure/FAILING_UPGRADE_OUTPUT_V12_10_42.txt`

## Findings

- **sqlite_operational_error** — SQLite rejected generated DDL. Repair: Use portable SQLAlchemy types and remove dialect-specific expressions.

## Created approved tables before failure

- `spine_connector_runs`
- `spine_dossier_assertions`
- `spine_raw_artifacts`
- `spine_observations`
- `spine_seeds`
- `spine_subjects`
- `spine_validation_events`
- `retention_runs`
- `workbench_jobs`
- `identity_edges`
- `identity_graphs`
- `identity_merge_candidates`
- `identity_nodes`
- `spine_contradictions`
- `policy_gate_events`
- `connector_runs`

## Not-created approved tables

- `identity_columns` ← probable first failure
- `all_tab_identity_cols`

## Probable failing table columns
