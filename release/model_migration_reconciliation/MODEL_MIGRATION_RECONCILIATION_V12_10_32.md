# v12.10.32 Model/Migration Reconciliation Audit

## Result

- **schema_mutation**: `none`
- **migration_created**: `False`
- **model tables**: `219`
- **migration tables**: `33`
- **missing model tables from migrations**: `202`
- **migration-only tables**: `16`

## Priority counts

- **EXCLUDE_OR_REVIEW**: `95`
- **P0**: `16`
- **P1**: `4`
- **P2**: `10`
- **P3**: `77`

## Status counts

- **active_candidate**: `24`
- **test_or_fixture**: `97`
- **unknown_review**: `81`

## Domain counts

- **auth**: `8`
- **connectors**: `5`
- **dossier**: `1`
- **evidence**: `1`
- **graph**: `3`
- **identity**: `12`
- **policy**: `1`
- **system**: `14`
- **timeline**: `3`
- **uncategorized**: `154`

## Ranked missing tables

| Priority | Score | Table | Domain | Status | Action | Sources | Hints |
|---|---:|---|---|---|---|---|---:|
| P0 | 89 | `spine_connector_runs` | connectors | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_dossier_assertions` | dossier | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_raw_artifacts` | evidence | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_observations` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_seeds` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_subjects` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 89 | `spine_validation_events` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | scripts/write_spine_files.py<br>src/socmint/database.py | 0 |
| P0 | 85 | `retention_runs` | connectors | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `workbench_jobs` | connectors | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `identity_columns` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P0 | 85 | `identity_edges` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `identity_graphs` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `identity_merge_candidates` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `identity_nodes` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `spine_contradictions` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P0 | 85 | `policy_gate_events` | policy | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P1 | 70 | `connector_runs` | connectors | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | src/socmint/database.py | 0 |
| P1 | 70 | `all_tab_identity_cols` | identity | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P1 | 65 | `media_profile_enrichments` | connectors | active_candidate | human_review_for_rename_or_indirect_coverage | src/socmint/database.py | 2 |
| P1 | 60 | `employee` | uncategorized | active_candidate | candidate_for_explicit_alembic_migration_after_column_review | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/mapper.py | 0 |
| P2 | 50 | `my_table` | timeline | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/sqlite/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/_orm_constructors.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py | 0 |
| P2 | 50 | `findings` | uncategorized | active_candidate | review_before_migration | src/socmint/database.py | 0 |
| P2 | 45 | `all_users` | auth | active_candidate | human_review_for_rename_or_indirect_coverage | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 1 |
| P2 | 45 | `user_order` | auth | active_candidate | human_review_for_rename_or_indirect_coverage | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py | 1 |
| P2 | 45 | `user_table` | auth | active_candidate | human_review_for_rename_or_indirect_coverage | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/dml.py | 1 |
| P2 | 45 | `all_db_links` | graph | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P2 | 45 | `edge` | graph | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/selectable.py | 0 |
| P2 | 45 | `relationships` | graph | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/decl_api.py | 0 |
| P2 | 35 | `event` | timeline | unknown_review | human_review_for_rename_or_indirect_coverage | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/compiler.py | 5 |
| P2 | 35 | `sometable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/named_types.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/sqlite/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/schema.py | 0 |
| P3 | 33 | `my_data` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/mutable.py | 0 |
| P3 | 33 | `person` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/indexable.py | 0 |
| P3 | 31 | `manager` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py | 0 |
| P3 | 31 | `slide` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/orderinglist.py | 0 |
| P3 | 29 | `bat` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/autogenerate/api.py | 0 |
| P3 | 29 | `bullet` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/orderinglist.py | 0 |
| P3 | 29 | `data` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/sqltypes.py | 0 |
| P3 | 29 | `engineer` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py | 0 |
| P3 | 29 | `searchword` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/hybrid.py | 0 |
| P3 | 26 | `account` | uncategorized | unknown_review | human_review_for_rename_or_indirect_coverage | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/hybrid.py | 1 |
| P3 | 25 | `pg_am` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_attrdef` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_attribute` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_class` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_collation` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_constraint` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_description` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_enum` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_index` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_namespace` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_opclass` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_sequence` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `pg_type` | system | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/pg_catalog.py | 0 |
| P3 | 25 | `COLUMNS` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `CONSTRAINT_COLUMN_USAGE` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `KEY_COLUMN_USAGE` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `MYTABLE` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py | 0 |
| P3 | 25 | `Markup` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/markup.py | 0 |
| P3 | 25 | `MyTable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py | 0 |
| P3 | 25 | `Name` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/default_styles.py | 0 |
| P3 | 25 | `REFERENTIAL_CONSTRAINTS` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `SCHEMATA` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `SEQUENCES` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `TABLES` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `TABLE_CONSTRAINTS` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `VIEWS` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `all_col_comments` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_cons_columns` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_constraints` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_ind_columns` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_ind_expressions` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_indexes` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_mview_comments` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_mviews` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_objects` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_sequences` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_synonyms` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_tab_cols` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_tab_comments` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_tables` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `all_views` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/dictionary.py | 0 |
| P3 | 25 | `bar` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/autogenerate/api.py | 0 |
| P3 | 25 | `columns` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `company` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py | 0 |
| P3 | 25 | `computed_columns` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `default_constraints` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `extended_properties` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `fktable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py | 0 |
| P3 | 25 | `index` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/palette.py | 0 |
| P3 | 25 | `interval` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/hybrid.py | 0 |
| P3 | 25 | `myothertable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py | 0 |
| P3 | 25 | `orders` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/selectable.py | 0 |
| P3 | 25 | `part` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/query.py | 0 |
| P3 | 25 | `parts` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/selectable.py | 0 |
| P3 | 25 | `referring` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py | 0 |
| P3 | 25 | `someothertable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/util.py | 0 |
| P3 | 25 | `sometable_one` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/named_types.py | 0 |
| P3 | 25 | `sometable_two` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/named_types.py | 0 |
| P3 | 25 | `table_b` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py | 0 |
| P3 | 25 | `types` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/information_schema.py | 0 |
| P3 | 25 | `unit_price` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/orm/_orm_constructors.py | 0 |
| P3 | 25 | `venue` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/functions.py | 0 |
| P3 | 25 | `vertices` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/mutable.py | 0 |
| P3 | 25 | `visitors` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/selectable.py | 0 |
| P3 | 25 | `yetanothertable` | uncategorized | unknown_review | review_before_migration | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/declarative/extensions.py | 0 |
| P3 | 15 | `user` | identity | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_computed.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_identity.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/engine/reflection.py | 1 |
| P3 | 15 | `some_table` | timeline | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_comments.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py | 0 |
| EXCLUDE_OR_REVIEW | 0 | `a` | auth | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_diffs.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/asyncio/session.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 10 |
| EXCLUDE_OR_REVIEW | 0 | `a_things_with_stuff` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | 0 | `data_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/hstore.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/json.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/sqltypes.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | 0 | `foo` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/autogenerate/api.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/live.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/pip/_vendor/rich/progress.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/compiler.py | 0 |
| EXCLUDE_OR_REVIEW | 0 | `mytable` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mysql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/array.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py | 0 |
| EXCLUDE_OR_REVIEW | 0 | `t` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/elements.py | 10 |
| EXCLUDE_OR_REVIEW | 0 | `test_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_ddl.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_results.py | 0 |
| EXCLUDE_OR_REVIEW | -2 | `ref` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py | 0 |
| EXCLUDE_OR_REVIEW | -2 | `test` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mssql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/fixtures/base.py | 0 |
| EXCLUDE_OR_REVIEW | -2 | `testtbl` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/sqlite/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `\u6e2c\u8a66` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_unicode_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `address` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/automap.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `autoinc_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `empty` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `manual_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_dialect.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `other` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `sa_cc` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `t1` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/oracle/base.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -4 | `x` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/fixtures.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 1 |
| EXCLUDE_OR_REVIEW | -6 | `b` | auth | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/ext/asyncio/session.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 7 |
| EXCLUDE_OR_REVIEW | -6 | `computed_column_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/fixtures/sql.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `employees` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_rowcount.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `no_constraints` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `order` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `plain_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_results.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_update_delete.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `quote ` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `ref_a` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `ref_b` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/test_autogen_fks.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `remote_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/schema.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `seq_no_returning_sch` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `square` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/sql/schema.py<br>var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `unicode_comments` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `x1` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `x2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `x3` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -6 | `x4` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `user_id_table` | auth | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 1 |
| EXCLUDE_OR_REVIEW | -10 | `user_orders` | auth | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 1 |
| EXCLUDE_OR_REVIEW | -10 | `users_ref` | auth | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 1 |
| EXCLUDE_OR_REVIEW | -10 | `thing` | system | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/config.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `Unitéble2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_unicode_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `_test_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `array_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `b_related_things_of_value` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `binary_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `bitwise` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `boolean_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `comment_test` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `computed_default_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/fixtures/sql.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `d_t` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `date_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `dingalings` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `email_addresses` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `empty_v` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `enum_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `extra` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `has_dates` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_results.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `includes_defaults` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `integer_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `interval_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `is_distinct_test` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `item` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `local_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `new_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `no_implicit_returning` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_insert.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `noncol_idx_test_nopk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `noncol_idx_test_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `percent%table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_results.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `related` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `remote_table_2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `sa_multi_index` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `seq_no_returning` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `seq_opt_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `seq_pk` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_sequence.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `some_other_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_cte.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `stuff` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `t2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `tb1` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `tb2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `tbl` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `tbl_a` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `tbl_b` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_select.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `test_table_2` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `test_table_s` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_reflection.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `testtable` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mysql/base.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `text_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `ts_test` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/dialects/mysql/base.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `unicode_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `unitable1` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_unicode_ddl.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `unnamed_sqlite` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `uuid_table` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_types.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `x5` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `x6` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/alembic/testing/suite/_autogen_fixtures.py | 0 |
| EXCLUDE_OR_REVIEW | -10 | `測試` | uncategorized | test_or_fixture | exclude_from_schema; confirm test-only | var/venvs/v12_10_17/lib/python3.13/site-packages/sqlalchemy/testing/suite/test_unicode_ddl.py | 10 |

## Migration-only tables

- `analyst_decisions`
- `billing_customer_links`
- `billing_events`
- `case_assignments`
- `checkout_sessions`
- `continuous_monitoring_events`
- `evidence_hash_events`
- `hidden_service_status`
- `intel_runs`
- `membership_plans`
- `quota_overrides`
- `strategic_risk_scores`
- `team_memberships`
- `usage_counters`
- `usage_events`
- `user_memberships`