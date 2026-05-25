# v12.10.48 Full DB Smoke Trace Capture

- **upgrade_returncode**: `1`
- **alembic_version_after_upgrade**: `0017_v12_10_schema_reconciliation`
- **schema_mutation**: `temp_sqlite_only`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **created_approved_table_count**: `16`
- **missing_approved_table_count**: `2`
- **full_upgrade_output**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_FULL_OUTPUT_V12_10_48.txt`
- **full_sql_output**: `/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_SQL_MODE_V12_10_48.sql`

## Exact exception

`sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table spine_connector_runs already exists`

## Findings

- **already_exists** / `blocker` — The migration creates an object already present from earlier migration; guard or remove duplicate create.
- **foreign_key_reference_issue** / `blocker` — Remove/defer FK references for temp SQLite smoke.

## Missing approved tables

- `identity_columns`
- `all_tab_identity_cols`

## Exception lines

- `Traceback (most recent call last):`
- `sqlite3.OperationalError: table spine_connector_runs already exists`
- `Traceback (most recent call last):`
- `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table spine_connector_runs already exists`
- `(Background on this error at: https://sqlalche.me/e/20/e3q8)`