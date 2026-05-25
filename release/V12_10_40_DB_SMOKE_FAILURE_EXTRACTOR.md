# v12.10.40 — DB Smoke Failure Extractor + Repair Target Report

Purpose:
1. Read v12.10.38 DB smoke JSON and v12.10.39 gate JSON.
2. Extract exact failing Alembic step.
3. Extract SQLite/Alembic exception lines.
4. Classify root cause.
5. Identify affected migration/table/column where possible.
6. Generate repair target report.
7. Do not mutate schema.
8. Do not run real DB upgrade.
