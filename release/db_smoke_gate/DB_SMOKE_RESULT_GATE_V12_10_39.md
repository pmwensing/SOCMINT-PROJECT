# v12.10.39 DB Smoke Result Gate

- **db_smoke_status**: `NO-GO`
- **release_status**: `HOLD`
- **schema_lock**: `DB_SMOKE_HOLD`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **temp_sqlite_only**: `True`
- **approved_table_count**: `18`
- **missing_after_upgrade_count**: `0`
- **lingering_after_downgrade_count**: `16`
- **version_after_upgrade**: `0018_approved_model_migration`
- **version_after_downgrade**: `0017_v12_10_schema_reconciliation`
- **next_action**: `repair 0018 migration or smoke incompatibility before release`

## Findings

- **sqlite_dialect_incompatibility** / review: Adjust migration for SQLite-safe smoke or use batch_alter_table/portable SQLAlchemy types.
- **downgrade_failure_or_lingering_tables** / blocker: Fix drop order and downgrade symmetry for 0018 approved tables.

## v12.10.38 errors

- approved 0018 tables still exist after downgrade to 0017: connector_runs, identity_edges, identity_graphs, identity_merge_candidates, identity_nodes, policy_gate_events, retention_runs, spine_connector_runs, spine_contradictions, spine_dossier_assertions, spine_observations, spine_raw_artifacts, spine_seeds, spine_subjects, spine_validation_events, workbench_jobs