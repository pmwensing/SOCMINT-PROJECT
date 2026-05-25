# v12.10.40 DB Smoke Repair Targets

Use this to build v12.10.41. Do not patch blindly.

## Targeted repairs

### unresolved_todo_symbol

- severity: `blocker`
- reason: Generated migration contains executable TODO placeholder.
- repair: Convert TODO placeholders into comments and use executable safe defaults.


## Safety constraints for v12.10.41

- Patch only `migrations/versions/0018_approved_model_migration.py` and the draft generator if needed.
- Do not run real DB upgrade.
- Rerun `make report121038` after repair.
- Gate again with `make report121039`.