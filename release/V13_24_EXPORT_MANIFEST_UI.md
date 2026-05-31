# v13.24 — Export Manifest UI

## Purpose

Make the export manifest draft visible as a subject-level analyst page.

## Added

- `src/socmint/export_manifest_ui_routes_v13.py`
  - Adds a subject-level manifest page backed by the v13.19 manifest draft service.

- `src/socmint/templates/export_manifest.html`
  - Shows manifest state, entry count, readiness state, ledger summary, entries, links, and notes.

- Route:
  - `GET /subjects/<subject_id>/export-manifest`

- Tests:
  - `tests/test_export_manifest_ui_routes_v13.py`

## Value

Analysts can preview expected export package components without opening raw JSON.
