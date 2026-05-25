# v12.10.49 — Existing Table Collision Guard

Purpose:
1. Use v12.10.48 exact blocker: `table spine_connector_runs already exists`.
2. Build a temp SQLite DB to Alembic `0017_v12_10_schema_reconciliation`.
3. Compare 0017 baseline tables against 0018 `op.create_table(...)` tables.
4. Detect collision tables already present before 0018.
5. Neutralize only collision table create/drop blocks in promoted 0018.
6. Preserve review notes as comments.
7. Rerun temp DB smoke and gate.
8. Do not run real configured DB upgrade.
9. Do not touch production DB.
