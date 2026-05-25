# v12.10.48 — Full DB Smoke Trace Capture + Identity Failure Classifier

Purpose:
1. Re-run the v12.10.38 temp SQLite smoke with maximum captured output.
2. Preserve full Alembic stdout/stderr, not truncated tails.
3. Capture temp DB table state after failure.
4. Extract exact exception class/message.
5. Extract probable failing SQL/table/column.
6. Dump the full `all_tab_identity_cols` and `identity_columns` blocks.
7. Produce a next-patch decision report.
8. Do not mutate schema.
9. Do not run real configured DB upgrade.
10. Do not touch production DB.
