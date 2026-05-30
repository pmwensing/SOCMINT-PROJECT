# v13.17 — Dossier Readiness UI

## Purpose

Make the dossier readiness gate visible to analysts instead of API-only.

## Added

- `src/socmint/dossier_readiness_ui_routes_v13.py`
  - Adds a subject-level readiness page.

- `src/socmint/templates/dossier_readiness.html`
  - Shows readiness state, blockers, warnings, counts, export booleans, and next actions.

- Route:
  - `GET /subjects/<subject_id>/dossier/readiness`

- Tests:
  - `tests/test_dossier_readiness_ui_routes_v13.py`

## Value

Analysts can see exactly why a dossier is blocked, draft-ready, final-ready, or exported before taking the next action.
