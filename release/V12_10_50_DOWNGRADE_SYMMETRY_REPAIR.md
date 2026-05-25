# v12.10.50 — Downgrade Symmetry Repair + Final DB Smoke Gate

Purpose:
1. Use v12.10.49 result: upgrade to 0018 succeeds.
2. Fix remaining DB smoke blocker: lingering 0018 tables after downgrade.
3. Compare approved 0018 created tables against active downgrade drop_table calls.
4. Restore missing/disabled downgrade drop calls for 0018-owned tables only.
5. Preserve collision/baseline safety: do not drop tables that existed at 0017.
6. Rerun temp SQLite DB smoke and gate.
7. Do not run real configured DB upgrade.
8. Do not touch production DB.
