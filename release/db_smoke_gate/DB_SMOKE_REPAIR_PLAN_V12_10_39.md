# v12.10.39 DB Smoke Repair Plan

DB smoke is not GO. Do not release and do not run a real DB upgrade.

## Repair queue

### sqlite_dialect_incompatibility

- severity: `review`
- repair: Adjust migration for SQLite-safe smoke or use batch_alter_table/portable SQLAlchemy types.

## Safety

- production_db_touched: `False` expected
- real_config_upgrade_run: `False` expected
- schema mutation allowed only on temp SQLite smoke DB

## Next

Fix the promoted 0018 migration or smoke compatibility, rerun `make report121038`, then rerun `make report121039`.