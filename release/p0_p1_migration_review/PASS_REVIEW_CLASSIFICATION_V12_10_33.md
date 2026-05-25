# v12.10.33 PASS/REVIEW Classification

| Classification | Table | Priority | Domain | Blockers | Warnings |
|---|---|---|---|---|---|
| PASS | `spine_connector_runs` | P0 | connectors | - | - |
| PASS | `spine_dossier_assertions` | P0 | dossier | - | - |
| PASS | `spine_raw_artifacts` | P0 | evidence | - | - |
| PASS | `spine_observations` | P0 | identity | - | - |
| PASS | `spine_seeds` | P0 | identity | - | - |
| PASS | `spine_subjects` | P0 | identity | - | - |
| PASS | `spine_validation_events` | P0 | identity | - | - |
| PASS | `retention_runs` | P0 | connectors | - | - |
| PASS | `workbench_jobs` | P0 | connectors | - | - |
| PASS | `identity_columns` | P0 | identity | - | - |
| PASS | `identity_edges` | P0 | identity | - | - |
| PASS | `identity_graphs` | P0 | identity | - | - |
| PASS | `identity_merge_candidates` | P0 | identity | - | - |
| PASS | `identity_nodes` | P0 | identity | - | - |
| PASS | `spine_contradictions` | P0 | identity | - | - |
| PASS | `policy_gate_events` | P0 | policy | - | - |
| PASS | `connector_runs` | P1 | connectors | - | - |
| PASS | `all_tab_identity_cols` | P1 | identity | - | - |
| PASS_WITH_REVIEW_NOTES | `media_profile_enrichments` | P1 | connectors | - | possible indirect/rename coverage exists |
| REVIEW | `employee` | P1 | uncategorized | no SQLAlchemy column hints extracted | - |