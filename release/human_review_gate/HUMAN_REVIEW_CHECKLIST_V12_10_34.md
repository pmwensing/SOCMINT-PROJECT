# v12.10.34 Human Review Checklist

- **schema_mutation**: `none`
- **migration_created**: `False`
- **alembic_versions_mutated**: `False`
- **candidate_count**: `20`
- **PASS queue**: `18`
- **PASS_WITH_REVIEW_NOTES queue**: `1`
- **REVIEW queue**: `1`

## Instructions

1. Review every table below.
2. Do not approve any table with unresolved blockers.
3. For PASS_WITH_REVIEW_NOTES, confirm warning notes manually.
4. For REVIEW, resolve blockers before approval.
5. Create/edit `release/human_review_gate/approval_list.json` manually.
6. Run `make approve121034` to build `approved_migration_set.json`.

## Required approval file format

```json
{
  "approved_by": "human-name-or-initials",
  "approval_date": "YYYY-MM-DD",
  "approved_tables": [
    "table_name_here"
  ],
  "notes": "manual review notes"
}
```

## Checklist

| Approve? | Classification | Priority | Table | Domain | Columns | Blockers | Warnings | Sources |
|---|---|---|---|---|---:|---|---|---|
| ☐ | PASS | P0 | `spine_connector_runs` | connectors | 14 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_dossier_assertions` | dossier | 18 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_raw_artifacts` | evidence | 18 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_observations` | identity | 20 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_seeds` | identity | 14 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_subjects` | identity | 6 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `spine_validation_events` | identity | 12 | - | - | scripts/write_spine_files.py<br>src/socmint/database.py |
| ☐ | PASS | P0 | `retention_runs` | connectors | 6 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `workbench_jobs` | connectors | 14 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `identity_columns` | identity | 8 | - | - | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py |
| ☐ | PASS | P0 | `identity_edges` | identity | 10 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `identity_graphs` | identity | 4 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `identity_merge_candidates` | identity | 12 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `identity_nodes` | identity | 9 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `spine_contradictions` | identity | 12 | - | - | src/socmint/database.py |
| ☐ | PASS | P0 | `policy_gate_events` | policy | 7 | - | - | src/socmint/database.py |
| ☐ | PASS | P1 | `connector_runs` | connectors | 10 | - | - | src/socmint/database.py |
| ☐ | PASS | P1 | `all_tab_identity_cols` | identity | 73 | - | - | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py |
| ☐ | PASS_WITH_REVIEW_NOTES | P1 | `media_profile_enrichments` | connectors | 9 | - | possible indirect/rename coverage exists | src/socmint/database.py |
| ☐ | REVIEW | P1 | `employee` | uncategorized | 0 | no SQLAlchemy column hints extracted | - | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py |

## Queue: PASS

### `spine_connector_runs`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `14`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_dossier_assertions`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `dossier`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `18`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_raw_artifacts`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `evidence`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `18`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_observations`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `20`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_seeds`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `14`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_subjects`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `6`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `spine_validation_events`

- classification: `PASS`
- priority: `P0` / `89`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `12`

Sources:
- `scripts/write_spine_files.py`
- `src/socmint/database.py`

### `retention_runs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `6`

Sources:
- `src/socmint/database.py`

### `workbench_jobs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `14`

Sources:
- `src/socmint/database.py`

### `identity_columns`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `8`

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py`

### `identity_edges`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `10`

Sources:
- `src/socmint/database.py`

### `identity_graphs`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `4`

Sources:
- `src/socmint/database.py`

### `identity_merge_candidates`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `12`

Sources:
- `src/socmint/database.py`

### `identity_nodes`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `9`

Sources:
- `src/socmint/database.py`

### `spine_contradictions`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `12`

Sources:
- `src/socmint/database.py`

### `policy_gate_events`

- classification: `PASS`
- priority: `P0` / `85`
- domain: `policy`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `7`

Sources:
- `src/socmint/database.py`

### `connector_runs`

- classification: `PASS`
- priority: `P1` / `70`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `10`

Sources:
- `src/socmint/database.py`

### `all_tab_identity_cols`

- classification: `PASS`
- priority: `P1` / `70`
- domain: `identity`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `73`

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py`


## Queue: PASS_WITH_REVIEW_NOTES

### `media_profile_enrichments`

- classification: `PASS_WITH_REVIEW_NOTES`
- priority: `P1` / `65`
- domain: `connectors`
- status: `active_candidate`
- migration_action: `human_review_for_rename_or_indirect_coverage`
- column_count: `9`

Warnings:
- possible indirect/rename coverage exists

Possible indirect/rename coverage:
- `profiles` — normalized substring/pluralization similarity (medium)
- `media` — normalized substring/pluralization similarity (medium)

Sources:
- `src/socmint/database.py`


## Queue: REVIEW

### `employee`

- classification: `REVIEW`
- priority: `P1` / `60`
- domain: `uncategorized`
- status: `active_candidate`
- migration_action: `candidate_for_explicit_alembic_migration_after_column_review`
- column_count: `0`

Blockers:
- no SQLAlchemy column hints extracted

Sources:
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py`
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py`
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py`
- `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py`
