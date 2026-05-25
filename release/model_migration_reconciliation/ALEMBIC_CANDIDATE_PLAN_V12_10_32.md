# v12.10.32 Safe Alembic Candidate Plan

This is a **plan only**. It does not create or apply a migration.

## Preconditions before generating a real migration

1. Review each P0/P1 table and confirm it is used by the current runtime.
2. Extract actual column definitions from SQLAlchemy models.
3. Confirm table naming and possible renames.
4. Exclude tests, fixtures, samples, demos, archived, and legacy modules.
5. Run a dry-run migration on an empty database.
6. Run downgrade safety check.

## Candidate P0/P1 tables for explicit migration

### `spine_connector_runs`
- priority: `P0` / score `89`
- domain: `connectors`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:487` (__tablename__)
  - `src/socmint/database.py:766` (__tablename__)

### `spine_dossier_assertions`
- priority: `P0` / score `89`
- domain: `dossier`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:525` (__tablename__)
  - `src/socmint/database.py:804` (__tablename__)

### `spine_raw_artifacts`
- priority: `P0` / score `89`
- domain: `evidence`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:498` (__tablename__)
  - `src/socmint/database.py:777` (__tablename__)

### `spine_observations`
- priority: `P0` / score `89`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:511` (__tablename__)
  - `src/socmint/database.py:790` (__tablename__)

### `spine_seeds`
- priority: `P0` / score `89`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:476` (__tablename__)
  - `src/socmint/database.py:755` (__tablename__)

### `spine_subjects`
- priority: `P0` / score `89`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:469` (__tablename__)
  - `src/socmint/database.py:748` (__tablename__)

### `spine_validation_events`
- priority: `P0` / score `89`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `scripts/write_spine_files.py:538` (__tablename__)
  - `src/socmint/database.py:817` (__tablename__)

### `retention_runs`
- priority: `P0` / score `85`
- domain: `connectors`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1928` (__tablename__)

### `workbench_jobs`
- priority: `P0` / score `85`
- domain: `connectors`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1899` (__tablename__)

### `identity_columns`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `path/name contains active domain hint`
- sources:
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py:248` (Table())

### `identity_edges`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1397` (__tablename__)

### `identity_graphs`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1376` (__tablename__)

### `identity_merge_candidates`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1411` (__tablename__)

### `identity_nodes`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1384` (__tablename__)

### `spine_contradictions`
- priority: `P0` / score `85`
- domain: `identity`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1742` (__tablename__)

### `policy_gate_events`
- priority: `P0` / score `85`
- domain: `policy`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:1917` (__tablename__)

### `connector_runs`
- priority: `P1` / score `70`
- domain: `connectors`
- status: `active_candidate`
- reason: `declared under src/socmint`
- sources:
  - `src/socmint/database.py:120` (__tablename__)

### `all_tab_identity_cols`
- priority: `P1` / score `70`
- domain: `identity`
- status: `active_candidate`
- reason: `path/name contains active domain hint`
- sources:
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py:228` (Table())

### `employee`
- priority: `P1` / score `60`
- domain: `uncategorized`
- status: `active_candidate`
- reason: `path/name contains active domain hint`
- sources:
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py:514` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py:542` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py:55` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py:379` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:548` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:564` (__tablename__)
  - `var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py:583` (__tablename__)


## Tables requiring human review before migration

- `media_profile_enrichments` — P1 / connectors / active_candidate / human_review_for_rename_or_indirect_coverage
- `my_table` — P2 / timeline / unknown_review / review_before_migration
- `findings` — P2 / uncategorized / active_candidate / review_before_migration
- `all_users` — P2 / auth / active_candidate / human_review_for_rename_or_indirect_coverage
- `user_order` — P2 / auth / active_candidate / human_review_for_rename_or_indirect_coverage
- `user_table` — P2 / auth / active_candidate / human_review_for_rename_or_indirect_coverage
- `all_db_links` — P2 / graph / unknown_review / review_before_migration
- `edge` — P2 / graph / unknown_review / review_before_migration
- `relationships` — P2 / graph / unknown_review / review_before_migration
- `event` — P2 / timeline / unknown_review / human_review_for_rename_or_indirect_coverage
- `sometable` — P2 / uncategorized / unknown_review / review_before_migration
- `my_data` — P3 / uncategorized / unknown_review / review_before_migration
- `person` — P3 / uncategorized / unknown_review / review_before_migration
- `manager` — P3 / uncategorized / unknown_review / review_before_migration
- `slide` — P3 / uncategorized / unknown_review / review_before_migration
- `bat` — P3 / uncategorized / unknown_review / review_before_migration
- `bullet` — P3 / uncategorized / unknown_review / review_before_migration
- `data` — P3 / uncategorized / unknown_review / review_before_migration
- `engineer` — P3 / uncategorized / unknown_review / review_before_migration
- `searchword` — P3 / uncategorized / unknown_review / review_before_migration
- `account` — P3 / uncategorized / unknown_review / human_review_for_rename_or_indirect_coverage
- `pg_am` — P3 / system / unknown_review / review_before_migration
- `pg_attrdef` — P3 / system / unknown_review / review_before_migration
- `pg_attribute` — P3 / system / unknown_review / review_before_migration
- `pg_class` — P3 / system / unknown_review / review_before_migration
- `pg_collation` — P3 / system / unknown_review / review_before_migration
- `pg_constraint` — P3 / system / unknown_review / review_before_migration
- `pg_description` — P3 / system / unknown_review / review_before_migration
- `pg_enum` — P3 / system / unknown_review / review_before_migration
- `pg_index` — P3 / system / unknown_review / review_before_migration
- `pg_namespace` — P3 / system / unknown_review / review_before_migration
- `pg_opclass` — P3 / system / unknown_review / review_before_migration
- `pg_sequence` — P3 / system / unknown_review / review_before_migration
- `pg_type` — P3 / system / unknown_review / review_before_migration
- `COLUMNS` — P3 / uncategorized / unknown_review / review_before_migration
- `CONSTRAINT_COLUMN_USAGE` — P3 / uncategorized / unknown_review / review_before_migration
- `KEY_COLUMN_USAGE` — P3 / uncategorized / unknown_review / review_before_migration
- `MYTABLE` — P3 / uncategorized / unknown_review / review_before_migration
- `Markup` — P3 / uncategorized / unknown_review / review_before_migration
- `MyTable` — P3 / uncategorized / unknown_review / review_before_migration
- `Name` — P3 / uncategorized / unknown_review / review_before_migration
- `REFERENTIAL_CONSTRAINTS` — P3 / uncategorized / unknown_review / review_before_migration
- `SCHEMATA` — P3 / uncategorized / unknown_review / review_before_migration
- `SEQUENCES` — P3 / uncategorized / unknown_review / review_before_migration
- `TABLES` — P3 / uncategorized / unknown_review / review_before_migration
- `TABLE_CONSTRAINTS` — P3 / uncategorized / unknown_review / review_before_migration
- `VIEWS` — P3 / uncategorized / unknown_review / review_before_migration
- `all_col_comments` — P3 / uncategorized / unknown_review / review_before_migration
- `all_cons_columns` — P3 / uncategorized / unknown_review / review_before_migration
- `all_constraints` — P3 / uncategorized / unknown_review / review_before_migration
- `all_ind_columns` — P3 / uncategorized / unknown_review / review_before_migration
- `all_ind_expressions` — P3 / uncategorized / unknown_review / review_before_migration
- `all_indexes` — P3 / uncategorized / unknown_review / review_before_migration
- `all_mview_comments` — P3 / uncategorized / unknown_review / review_before_migration
- `all_mviews` — P3 / uncategorized / unknown_review / review_before_migration
- `all_objects` — P3 / uncategorized / unknown_review / review_before_migration
- `all_sequences` — P3 / uncategorized / unknown_review / review_before_migration
- `all_synonyms` — P3 / uncategorized / unknown_review / review_before_migration
- `all_tab_cols` — P3 / uncategorized / unknown_review / review_before_migration
- `all_tab_comments` — P3 / uncategorized / unknown_review / review_before_migration
- `all_tables` — P3 / uncategorized / unknown_review / review_before_migration
- `all_views` — P3 / uncategorized / unknown_review / review_before_migration
- `bar` — P3 / uncategorized / unknown_review / review_before_migration
- `columns` — P3 / uncategorized / unknown_review / review_before_migration
- `company` — P3 / uncategorized / unknown_review / review_before_migration
- `computed_columns` — P3 / uncategorized / unknown_review / review_before_migration
- `default_constraints` — P3 / uncategorized / unknown_review / review_before_migration
- `extended_properties` — P3 / uncategorized / unknown_review / review_before_migration
- `fktable` — P3 / uncategorized / unknown_review / review_before_migration
- `index` — P3 / uncategorized / unknown_review / review_before_migration
- `interval` — P3 / uncategorized / unknown_review / review_before_migration
- `myothertable` — P3 / uncategorized / unknown_review / review_before_migration
- `orders` — P3 / uncategorized / unknown_review / review_before_migration
- `part` — P3 / uncategorized / unknown_review / review_before_migration
- `parts` — P3 / uncategorized / unknown_review / review_before_migration
- `referring` — P3 / uncategorized / unknown_review / review_before_migration
- `someothertable` — P3 / uncategorized / unknown_review / review_before_migration
- `sometable_one` — P3 / uncategorized / unknown_review / review_before_migration
- `sometable_two` — P3 / uncategorized / unknown_review / review_before_migration
- `table_b` — P3 / uncategorized / unknown_review / review_before_migration
- `types` — P3 / uncategorized / unknown_review / review_before_migration
- `unit_price` — P3 / uncategorized / unknown_review / review_before_migration
- `venue` — P3 / uncategorized / unknown_review / review_before_migration
- `vertices` — P3 / uncategorized / unknown_review / review_before_migration
- `visitors` — P3 / uncategorized / unknown_review / review_before_migration
- `yetanothertable` — P3 / uncategorized / unknown_review / review_before_migration
- `user` — P3 / identity / test_or_fixture / exclude_from_schema; confirm test-only
- `some_table` — P3 / timeline / test_or_fixture / exclude_from_schema; confirm test-only
- `a` — EXCLUDE_OR_REVIEW / auth / test_or_fixture / exclude_from_schema; confirm test-only
- `a_things_with_stuff` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `data_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `foo` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `mytable` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `t` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `test_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `ref` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `test` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `testtbl` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `\u6e2c\u8a66` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `address` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `autoinc_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `empty` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `manual_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `other` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `sa_cc` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `t1` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `b` — EXCLUDE_OR_REVIEW / auth / test_or_fixture / exclude_from_schema; confirm test-only
- `computed_column_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `employees` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `no_constraints` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `order` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `plain_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `quote ` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `ref_a` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `ref_b` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `remote_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `seq_no_returning_sch` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `square` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `unicode_comments` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x1` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x3` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x4` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `user_id_table` — EXCLUDE_OR_REVIEW / auth / test_or_fixture / exclude_from_schema; confirm test-only
- `user_orders` — EXCLUDE_OR_REVIEW / auth / test_or_fixture / exclude_from_schema; confirm test-only
- `users_ref` — EXCLUDE_OR_REVIEW / auth / test_or_fixture / exclude_from_schema; confirm test-only
- `thing` — EXCLUDE_OR_REVIEW / system / test_or_fixture / exclude_from_schema; confirm test-only
- `Unitéble2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `_test_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `array_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `b_related_things_of_value` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `binary_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `bitwise` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `boolean_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `comment_test` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `computed_default_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `d_t` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `date_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `dingalings` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `email_addresses` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `empty_v` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `enum_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `extra` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `has_dates` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `includes_defaults` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `integer_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `interval_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `is_distinct_test` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `item` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `local_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `new_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `no_implicit_returning` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `noncol_idx_test_nopk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `noncol_idx_test_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `percent%table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `related` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `remote_table_2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `sa_multi_index` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `seq_no_returning` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `seq_opt_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `seq_pk` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `some_other_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `stuff` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `t2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `tb1` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `tb2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `tbl` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `tbl_a` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `tbl_b` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `test_table_2` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `test_table_s` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `testtable` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `text_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `ts_test` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `unicode_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `unitable1` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `unnamed_sqlite` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `uuid_table` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x5` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `x6` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only
- `測試` — EXCLUDE_OR_REVIEW / uncategorized / test_or_fixture / exclude_from_schema; confirm test-only

## Skeleton for later manual migration

```python
"""v12.10.33 reviewed model/migration reconciliation

Revision ID: 0018_reviewed_model_migration_reconciliation
Revises: 0017_v12_10_schema_reconciliation
"""

# This skeleton is intentionally incomplete.
# Fill columns manually after reviewing SQLAlchemy models.

from alembic import op
import sqlalchemy as sa

revision = "0018_reviewed_model_migration_reconciliation"
down_revision = "0017_v12_10_schema_reconciliation"
branch_labels = None
depends_on = None

def upgrade():
    # create reviewed tables only
    pass

def downgrade():
    # drop reviewed tables only, reverse dependency order
    pass
```