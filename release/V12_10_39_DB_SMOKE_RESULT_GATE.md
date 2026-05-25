# v12.10.39 — DB Smoke Result Gate + Repair Planner

Purpose:
1. Read v12.10.38 DB smoke report.
2. If smoke_status is GO, produce a promotion-ready manifest.
3. If smoke_status is NO-GO, produce a repair plan.
4. Classify failures: SQLite incompatibility, migration syntax, missing tables, downgrade issues, version issues.
5. Do not run alembic upgrade against real DB.
6. Do not mutate schema.
7. Keep release_status HOLD unless DB smoke is GO.
