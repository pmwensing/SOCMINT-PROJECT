# v13.35 Final — Correlation Scope Closure Gate

## Purpose

v13.35 final closes the case/correlation scope correctness line after the A-D follow-up builds. The accepted result is a DB-backed, quarantine-first scope model that keeps separate initial searches isolated unless same-scope, analyst-merged, or deterministic same-target proof exists.

## Included builds

- `V13_35_CASE_SCOPE_ENFORCEMENT.md`: case-bound spine subjects, case-filtered listing, and seed/run scope validation.
- `V13_35A_CORRELATION_SCOPE_AUDIT.md`: audit-first route and policy gate for missing persistent scope coverage.
- `V13_35B_CORRELATION_SCOPE_ENFORCEMENT.md`: persistent scope-column migration and deterministic promotion decisions.
- `V13_35C_CORRELATION_SCOPE_WRITE_PATH.md`: write-path propagation and deterministic legacy backfill foundation.
- `V13_35D_CORRELATION_SCOPE_DB_BACKFILL.md`: DB model integration, proof route, and admin backfill command.

## Operator acceptance

- Existing spine databases can receive additive scope-column repair without broad schema auto-creation.
- Scope proof is available at `GET /api/v1/audit/correlation-scope/v13.35/db-proof`.
- Admin backfill is available at `POST /api/v1/admin/correlation-scope/v13.35/backfill`.
- Ambiguous cross-scope profile promotion remains quarantine-first.
- Two initial searches for the same display value remain isolated until there is explicit merge proof.

## Verification

- `make ci`
- Focused V13.35 suites:
  - `tests/test_case_scope_enforcement_v13_35.py`
  - `tests/test_v13_35A_correlation_scope_audit.py`
  - `tests/test_v13_35B_correlation_scope_enforcement.py`
  - `tests/test_v13_35C_correlation_scope_write_path.py`
  - `tests/test_v13_35D_correlation_scope_db_backfill.py`
- Runtime WSGI smoke against a freshly migrated SQLite database:
  - `GET /api/v1/audit/correlation-scope/v13.35/db-proof` -> `200`
  - `POST /api/v1/admin/correlation-scope/v13.35/backfill` -> `200`

## Non-goals

- No new connectors.
- No enrichment expansion.
- No broad UI redesign.
- No export blocker policy changes; those continue in the v13.36+ line.
