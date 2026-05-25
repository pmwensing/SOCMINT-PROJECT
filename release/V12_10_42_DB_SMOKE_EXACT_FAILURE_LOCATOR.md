# v12.10.42 — DB Smoke Exact Failure Capture + Failed Table Locator

Purpose:
1. Read v12.10.38 DB smoke JSON.
2. Extract full failing Alembic upgrade output.
3. Compare approved/create/drop order against actual temp SQLite tables.
4. Identify created tables, missing tables, and probable first failing table.
5. Extract promoted 0018 table blocks for missing/failing candidates.
6. Produce a targeted repair report.
7. Do not mutate schema.
8. Do not run real DB upgrade.
