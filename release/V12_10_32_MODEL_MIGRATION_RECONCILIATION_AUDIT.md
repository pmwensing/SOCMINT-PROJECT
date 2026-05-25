# v12.10.32 — Model/Migration Reconciliation Audit

Purpose:
- Audit model tables missing from Alembic migrations.
- Do **not** create tables.
- Do **not** mutate schema.
- Do **not** generate an executable migration that auto-applies changes.

Outputs:
- Ranked reconciliation report.
- Domain/module grouping.
- Active vs legacy/test/archive classification.
- Possible indirect/rename coverage hints.
- Safe Alembic candidate plan for human review.
