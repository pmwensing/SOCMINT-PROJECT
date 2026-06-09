# v13.35D — Correlation Scope Model Integration + DB Backfill Command

## Purpose

v13.35D moves correlation-scope work from helper-only foundations into DB-backed model integration and idempotent backfill/proof helpers.

## Scope

- Adds correlation-scope model fields to spine seed/run/observation/assertion models.
- Adds idempotent DB backfill helper.
- Adds DB-backed proof payload showing scope coverage.
- Adds API route for runtime proof.
- Adds DB-backed two-initial-search isolation tests.
- Preserves quarantine-first enforcement.

## Migration note

V13.35D relies on the existing `0018_v13_35b_correlation_scope_ids` Alembic migration for persistent scope columns. Runtime database configuration also performs additive schema repair for older spine databases that already have the spine tables but were started with auto-create disabled.

## Non-goals

- No new connectors.
- No enrichment expansion.
- No broad UI redesign.
- No final v13.35 tag.
