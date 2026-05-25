# v12.10.36 Approved Draft Static Validation

- **promotion_status**: `GO`
- **schema_mutation**: `none`
- **migration_created**: `False`
- **alembic_versions_mutated**: `False`
- **alembic_upgrade_run**: `False`
- **approved_table_count**: `18`
- **create_table_count**: `18`
- **drop_table_count**: `18`
- **todo_count**: `354`

## Errors

- none

## Warnings

- none

## Approved / upgrade / downgrade order

1. `spine_connector_runs`
2. `spine_dossier_assertions`
3. `spine_raw_artifacts`
4. `spine_observations`
5. `spine_seeds`
6. `spine_subjects`
7. `spine_validation_events`
8. `retention_runs`
9. `workbench_jobs`
10. `identity_columns`
11. `identity_edges`
12. `identity_graphs`
13. `identity_merge_candidates`
14. `identity_nodes`
15. `spine_contradictions`
16. `policy_gate_events`
17. `connector_runs`
18. `all_tab_identity_cols`