# v12.10.35 — Approved Migration Draft Builder

Purpose:
1. Read `release/human_review_gate/approved_migration_set.json`.
2. Refuse if approval is invalid.
3. Generate a reviewed, non-executed Alembic 0018 draft from approved tables only.
4. Keep draft outside `alembic/versions`.
5. Validate downgrade order.
6. Validate no unapproved REVIEW/PASS_WITH_REVIEW_NOTES table enters draft.
7. Do not run `alembic upgrade`.
8. Do not mutate schema.

Guarantees:
- No schema mutation.
- No Alembic upgrade.
- No file written to `alembic/versions`.
- Draft is review-only until explicitly promoted in a future build.
