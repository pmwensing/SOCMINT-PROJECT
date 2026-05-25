# v12.10.48 Next Patch Decision

Use this for v12.10.49. Do not patch blindly.

## Exact exception

`None`

## Findings

### foreign_key_reference_issue

- severity: `blocker`
- repair: Remove/defer FK references for temp SQLite smoke.

## Files to inspect

- `/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_FULL_OUTPUT_V12_10_48.txt`
- `/home/pmwens/Projects/SOCMINT-PROJECT/release/full_db_smoke_trace/ALEMBIC_UPGRADE_HEAD_SQL_MODE_V12_10_48.sql`
- `release/full_db_smoke_trace/IDENTITY_BLOCKS_FROM_0018_V12_10_48.md`

## Safety constraints

- Patch only promoted 0018 unless generator cause is proven.
- Keep TODOs as comments only.
- Do not run real DB upgrade.
- Rerun v12.10.38 and v12.10.39 after patch.