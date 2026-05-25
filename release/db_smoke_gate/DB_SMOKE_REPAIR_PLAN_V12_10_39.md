# v12.10.39 DB Smoke Repair Plan

DB smoke is not GO. Do not release and do not run a real DB upgrade.

## Repair queue

### unclassified_db_smoke_failure

- severity: `review`
- repair: Inspect DB_MIGRATION_SMOKE_V12_10_38.md step outputs manually.

## Safety

- production_db_touched: `False` expected
- real_config_upgrade_run: `False` expected
- schema mutation allowed only on temp SQLite smoke DB

## Next

Fix the promoted 0018 migration or smoke compatibility, rerun `make report121038`, then rerun `make report121039`.