# v12.10.34 — Human Review Gate + Approved Migration Set Builder

Purpose:
1. Read v12.10.33 P0/P1 candidate JSON.
2. Require explicit approval list before any migration draft can become executable.
3. Generate review checklist for 20 candidates.
4. Separate PASS / PASS_WITH_REVIEW_NOTES / REVIEW into queues.
5. Build `approved_migration_set.json`.
6. Refuse to create Alembic migration unless approval file exists.
7. Still no schema mutation by default.

Guarantees:
- No schema mutation.
- No Alembic migration is created.
- No files are written to `alembic/versions`.
- Approved migration set is review metadata only.
