# v13.19 — Export Manifest Draft

## Purpose

Add a non-ZIP manifest draft contract before implementing filesystem or package generation.

## Added

- `src/socmint/export_manifest_draft_v13.py`
  - Builds a manifest draft from dossier readiness, claim/evidence ledger, and subject status.

- `src/socmint/export_manifest_draft_routes_v13.py`
  - Adds a subject-level manifest draft API endpoint.

- Route:
  - `GET /api/v1/subjects/<subject_id>/export-manifest-draft`

- Tests:
  - `tests/test_export_manifest_draft_v13.py`

## Value

This creates a stable package checklist contract before adding ZIP or filesystem export.
