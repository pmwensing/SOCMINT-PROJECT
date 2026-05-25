# v12.10.37 — Migration Promotion Gate

Purpose:
1. Read v12.10.36 GO validation report.
2. Refuse promotion if `promotion_status != GO`.
3. Copy approved draft into `alembic/versions` as `0018_approved_model_migration.py`.
4. Strip review-only language but preserve TODO comments.
5. Do not run `alembic upgrade`.
6. Validate Alembic sees new head `0018_approved_model_migration`.
7. Produce promotion manifest.
8. Still no database schema mutation.

Guarantees:
- No database schema mutation.
- No `alembic upgrade`.
- Promotion only occurs if v12.10.36 validation report says GO.
