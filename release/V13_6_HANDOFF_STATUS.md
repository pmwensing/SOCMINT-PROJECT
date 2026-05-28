# v13.6 — Subject Handoff Status

## Purpose

Create a lightweight handoff readiness contract before building full downloadable package generation.

## Added

- `src/socmint/handoff_status_v13.py`
  - Combines dossier readiness, claim/evidence ledger coverage, and report availability.

- `src/socmint/handoff_status_routes_v13.py`
  - Adds a subject-level handoff status API endpoint.

- Route:
  - `GET /api/v1/subjects/<subject_id>/handoff-status`

- Tests:
  - `tests/test_handoff_status_v13.py`

## Status rows

```text
readiness
claim_coverage
report
verification
```

## States

```text
blocked
draft_ready
ready
```

## Value

This gives the future package/export workflow a stable checklist before file generation is added.
