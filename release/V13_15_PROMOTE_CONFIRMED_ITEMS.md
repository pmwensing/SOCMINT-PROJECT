# v13.15 — Promote Confirmed Items to Dossier Claims

## Purpose

Move analyst-confirmed normalized review items into the dossier assertion layer.

## Added

- `src/socmint/normalization_promote_confirmed_v13.py`
  - Promotes confirmed observations to confirmed dossier assertions.
  - Promotes confirmed account discoveries to confirmed dossier assertions.

- `src/socmint/normalization_promote_confirmed_routes_v13.py`
  - Adds a promotion API endpoint.

- Route:
  - `POST /api/v1/review/normalization-promote`

- Tests:
  - `tests/test_normalization_promote_confirmed_v13.py`

## Value

Reviewed connector output can now feed the dossier builder through a deliberate promotion step.
