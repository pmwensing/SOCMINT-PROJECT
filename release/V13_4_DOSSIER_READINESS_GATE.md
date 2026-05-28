# v13.4 — Dossier Readiness API + Gate

## Purpose

Make dossier readiness a reusable backend gate instead of only a lightweight command-center display.

## Added

- `src/socmint/dossier_readiness_v13.py`
  - Reusable readiness state machine.
  - Draft/final export booleans.
  - Blockers, warnings, counts, and next actions.

- `src/socmint/dossier_readiness_routes_v13.py`
  - Subject-level readiness endpoint.
  - Command-center readiness summary endpoint.

- Routes:
  - `GET /api/v1/subjects/<subject_id>/dossier/readiness`
  - `GET /api/v1/command-center/dossier-readiness`

- Tests:
  - `tests/test_dossier_readiness_v13.py`

## Readiness states

```text
blocked
needs_review
draft_ready
final_ready
exported
```

## Current checks

- No subject -> blocked.
- No seed/target -> blocked.
- Hash mismatch -> blocked.
- No findings -> needs review / collection.
- Pending review -> needs review.
- Promoted claim without evidence -> needs review.
- Unresolved contradiction -> needs review.
- Findings with no blockers -> draft ready.
- Existing report -> exported.

## Value

This gives dossier generation and future package export a real readiness contract that can be reused by UI, API, CI, and export gates.
