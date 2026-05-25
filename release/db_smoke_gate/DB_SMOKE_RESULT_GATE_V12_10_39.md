# v12.10.39 DB Smoke Result Gate

- **db_smoke_status**: `NO-GO`
- **release_status**: `HOLD`
- **schema_lock**: `DB_SMOKE_HOLD`
- **production_db_touched**: `False`
- **real_config_upgrade_run**: `False`
- **temp_sqlite_only**: `True`
- **approved_table_count**: `18`
- **missing_after_upgrade_count**: `2`
- **lingering_after_downgrade_count**: `16`
- **version_after_upgrade**: `0017_v12_10_schema_reconciliation`
- **version_after_downgrade**: `0017_v12_10_schema_reconciliation`
- **next_action**: `repair 0018 migration or smoke incompatibility before release`

## Findings

- **sqlite_dialect_incompatibility** / review: Adjust migration for SQLite-safe smoke or use batch_alter_table/portable SQLAlchemy types.

## v12.10.38 errors

- alembic upgrade head failed against temp SQLite DB