# SOCMINT v9.6.0 — Operator UX Smoke + Release Cleanup

## Summary

v9.6.0 ports the operator UX smoke matrix from the stale `smoke/v9-6-operator-ux` branch onto current `master` after v9.5.1. It adds admin-only smoke endpoints, focused tests, and release cleanup documentation.

## Source branch verification

`smoke/v9-6-operator-ux` was compared against current `master` after v9.5.1. The branch was useful but stale:

- status: diverged
- ahead of master: 3 commits
- behind master: 5 commits
- files identified for porting:
  - `src/socmint/operator_smoke.py`
  - `src/socmint/operator_smoke_routes.py`
  - `src/socmint/production_release_routes.py`

The smoke files were ported onto a fresh branch instead of merging the stale branch directly.

## Added

- Operator smoke matrix helper.
- Admin-only operator smoke routes.
- Production-release route integration.
- Focused operator smoke tests.
- Branch inventory and release cleanup checklist.

## Routes

- `GET /api/v1/admin/operator-smoke/matrix`
- `GET /api/v1/admin/operator-smoke/summary`
- `GET /api/v1/admin/operator-smoke/validate`

## Validation

Focused command:

```bash
python -m pytest tests/test_operator_smoke_v9_6.py
```

Full gate:

```bash
python -m pytest
```

## Merge gate

Merge only after focused tests and full CI pass.
