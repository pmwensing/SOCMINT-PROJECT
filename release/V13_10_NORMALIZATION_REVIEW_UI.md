# v13.10 — Normalization Review Queue UI

## Purpose

Make the normalization review queue visible to analysts instead of API-only.

## Added

- `src/socmint/normalization_review_ui_routes_v13.py`
  - Renders a review queue page using the v13.7 queue service.

- `src/socmint/templates/normalization_review_queue.html`
  - Shows review items, state counts, evidence references, and links to the API payload.

- Route:
  - `GET /review/normalization-queue`

- Tests:
  - `tests/test_normalization_review_ui_routes_v13.py`

## Value

Analysts can now see normalized connector output in a human-facing queue before it becomes dossier material.
