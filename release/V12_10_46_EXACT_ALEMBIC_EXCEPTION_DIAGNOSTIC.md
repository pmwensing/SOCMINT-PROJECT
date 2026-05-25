# v12.10.46 — Exact Alembic Exception + Identity Block DDL Diagnostic

Purpose:
1. Read v12.10.38 full failing upgrade output.
2. Extract the exact Python/Alembic/SQLAlchemy exception.
3. Extract the last traceback block.
4. Dump the `all_tab_identity_cols` and `identity_columns` create_table blocks.
5. Detect unsafe table/column patterns:
   - reserved names
   - repeated primary keys
   - invalid defaults
   - server defaults
   - unsupported SQLite constraints
   - malformed SQLAlchemy args
6. Produce an exact diagnostic report.
7. Do not mutate migration.
8. Do not run real DB upgrade.
9. Do not touch production DB.
