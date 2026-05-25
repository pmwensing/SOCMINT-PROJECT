# v12.10.46 Identity Repair Hints

Use this for v12.10.47. Do not patch blindly.

## Findings

### unclassified_exact_failure

- severity: `review`
- repair: Inspect failing output and identity table blocks manually; no known classifier matched.

## Next repair constraints

- Patch only `migrations/versions/0018_approved_model_migration.py` unless generator source clearly caused the issue.
- Keep TODO text as comments only.
- Do not run real DB upgrade.
- Rerun v12.10.38 and v12.10.39 after repair.