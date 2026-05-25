# v12.10.38 Dry-Run DB Migration Smoke Report

- **smoke_status**: `NO-GO`
- **schema_mutation**: `temp_sqlite_only`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **approved_table_count**: `18`
- **tables_after_upgrade_count**: `54`
- **missing_after_upgrade**: `0`
- **lingering_after_downgrade**: `16`
- **version_after_upgrade**: `0018_approved_model_migration`
- **version_after_downgrade**: `0017_v12_10_schema_reconciliation`
- **temp_db_path**: `/tmp/socmint_v12_10_38_2z0zy1ne/dry_run.sqlite`

## Errors

- approved 0018 tables still exist after downgrade to 0017: connector_runs, identity_edges, identity_graphs, identity_merge_candidates, identity_nodes, policy_gate_events, retention_runs, spine_connector_runs, spine_contradictions, spine_dossier_assertions, spine_observations, spine_raw_artifacts, spine_seeds, spine_subjects, spine_validation_events, workbench_jobs

## Warnings

- none

## Step outputs

### alembic_heads_temp_config returncode=0

```text
0018_approved_model_migration (head)

```

### upgrade_head_temp_sqlite returncode=0

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001_initial_schema -> 0002_audit_logs_and_indexes, audit logs and rate-limit indexes
INFO  [alembic.runtime.migration] Running upgrade 0002_audit_logs_and_indexes -> 0003_user_status_and_constraints, user status and stricter constraints
INFO  [alembic.runtime.migration] Running upgrade 0003_user_status_and_constraints -> 0004_roles_and_scan_jobs, roles and scan jobs
INFO  [alembic.runtime.migration] Running upgrade 0004_roles_and_scan_jobs -> 0005_v7_1_model_sync, v7.1 model sync
INFO  [alembic.runtime.migration] Running upgrade 0005_v7_1_model_sync -> 0006_v7_2_1_review_decisions, v7.2.1 review decision persistence
INFO  [alembic.runtime.migration] Running upgrade 0006_v7_2_1_review_decisions -> 0007_v7_2_2_review_decision_audit, v7.2.2 review decision audit trail and bulk actions
INFO  [alembic.runtime.migration] Running upgrade 0007_v7_2_2_review_decision_audit -> 0008_high_end_socmint_workflows, high-end SOCMINT workflow tables
INFO  [alembic.runtime.migration] Running upgrade 0008_high_end_socmint_workflows -> 0009_account_discovery_ingest, account discovery ingest table
INFO  [alembic.runtime.migration] Running upgrade 0009_account_discovery_ingest -> 0010_membership_quotas, membership and quota tables
INFO  [alembic.runtime.migration] Running upgrade 0010_membership_quotas -> 0011_billing, billing tables
INFO  [alembic.runtime.migration] Running upgrade 0011_billing -> 0012_tor_status, tor status table
INFO  [alembic.runtime.migration] Running upgrade 0012_tor_status -> 0013_billing_customer_links, billing customer links
INFO  [alembic.runtime.migration] Running upgrade 0013_billing_customer_links -> 0014_case_access, case access tables
INFO  [alembic.runtime.migration] Running upgrade 0014_case_access -> 0017_v12_10_schema_reconciliation, v12.10.30 schema reconciliation command-center tables
INFO  [alembic.runtime.migration] Running upgrade 0017_v12_10_schema_reconciliation -> 0018_approved_model_migration, v12.10.37 APPROVED MODEL MIGRATION

```

### downgrade_to_0017_temp_sqlite returncode=0

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0018_approved_model_migration -> 0017_v12_10_schema_reconciliation, v12.10.37 APPROVED MODEL MIGRATION

```
