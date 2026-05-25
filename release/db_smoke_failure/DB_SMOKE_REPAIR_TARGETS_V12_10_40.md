# v12.10.40 DB Smoke Repair Targets

Use this to build v12.10.41. Do not patch blindly.

## Targeted repairs

### duplicate_table_or_constraint

- severity: `blocker`
- reason: Migration attempted to create an object that already exists.
- repair: Add create-if-missing guards or fix duplicate table list.


## Safety constraints for v12.10.41

- Patch only `migrations/versions/0018_approved_model_migration.py` and the draft generator if needed.
- Do not run real DB upgrade.
- Rerun `make report121038` after repair.
- Gate again with `make report121039`.