# v13.35D — Correlation Scope Model Integration + DB Backfill Command

## Purpose

v13.35D moves correlation-scope work from helper-only foundations into DB-backed model integration and idempotent backfill/proof helpers.

## Scope

- Adds correlation-scope model fields to spine seed/run/observation/assertion models.
- Adds idempotent DB backfill helper.
- Adds DB-backed proof payload showing scope coverage.
- Adds API route for runtime proof.
- Adds admin-only API route for running the DB backfill.
- Adds DB-backed two-initial-search isolation tests.
- Preserves quarantine-first enforcement.

## Routes

- `GET /api/v1/audit/correlation-scope/v13.35/db-proof` requires login and returns DB-backed scope coverage.
- `POST /api/v1/admin/correlation-scope/v13.35/backfill` requires admin access and CSRF validation before running the idempotent backfill.

## Migration note

V13.35D relies on the existing `0018_v13_35b_correlation_scope_ids` Alembic migration for persistent scope columns. Runtime database configuration also performs additive schema repair for older spine databases that already have the spine tables but were started with auto-create disabled.

## Verification

- `make ci`
- Runtime WSGI smoke against a freshly migrated SQLite database:
  - `GET /api/v1/audit/correlation-scope/v13.35/db-proof` -> `200`
  - `POST /api/v1/admin/correlation-scope/v13.35/backfill` -> `200`

## Non-goals

- No new connectors.
- No enrichment expansion.
- No broad UI redesign.
- No final v13.35 tag.
