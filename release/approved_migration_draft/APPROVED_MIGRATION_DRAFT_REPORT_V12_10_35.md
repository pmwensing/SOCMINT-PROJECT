# v12.10.35 Approved Migration Draft Report

- **schema_mutation**: `none`
- **migration_created**: `False`
- **alembic_versions_mutated**: `False`
- **alembic_upgrade_run**: `False`
- **draft_created**: `True`
- **approved_table_count**: `18`
- **draft_path**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py`

## Approved tables

| Table | Classification | Domain | Priority | Columns |
|---|---|---|---|---:|
| `spine_connector_runs` | PASS | connectors | P0 | 7 |
| `spine_dossier_assertions` | PASS | dossier | P0 | 9 |
| `spine_raw_artifacts` | PASS | evidence | P0 | 9 |
| `spine_observations` | PASS | identity | P0 | 10 |
| `spine_seeds` | PASS | identity | P0 | 7 |
| `spine_subjects` | PASS | identity | P0 | 3 |
| `spine_validation_events` | PASS | identity | P0 | 6 |
| `retention_runs` | PASS | connectors | P0 | 6 |
| `workbench_jobs` | PASS | connectors | P0 | 14 |
| `identity_columns` | PASS | identity | P0 | 8 |
| `identity_edges` | PASS | identity | P0 | 10 |
| `identity_graphs` | PASS | identity | P0 | 4 |
| `identity_merge_candidates` | PASS | identity | P0 | 12 |
| `identity_nodes` | PASS | identity | P0 | 9 |
| `spine_contradictions` | PASS | identity | P0 | 12 |
| `policy_gate_events` | PASS | policy | P0 | 7 |
| `connector_runs` | PASS | connectors | P1 | 10 |
| `all_tab_identity_cols` | PASS | identity | P1 | 73 |

## Downgrade order

- `all_tab_identity_cols`
- `connector_runs`
- `policy_gate_events`
- `spine_contradictions`
- `identity_nodes`
- `identity_merge_candidates`
- `identity_graphs`
- `identity_edges`
- `identity_columns`
- `workbench_jobs`
- `retention_runs`
- `spine_validation_events`
- `spine_subjects`
- `spine_seeds`
- `spine_observations`
- `spine_raw_artifacts`
- `spine_dossier_assertions`
- `spine_connector_runs`

## Next required step

Review `0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py` manually.
Do not copy it into `alembic/versions` until a future promotion build explicitly approves it.