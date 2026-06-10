# v13.31 - Export Artifact UX Runtime Acceptance

## Purpose

Document the export artifact UX polish and runtime acceptance assets for Full Dossier v2.

## Added

- Latest Full Report Export card coverage in the Full Dossier v2 template.
- Artifact card/grid/action classes across full-report browser and history pages.
- Runtime visual CSS for export artifact layouts.
- Runtime acceptance and capture scripts:
  - `scripts/runtime_acceptance_v13_31.sh`
  - `scripts/capture_runtime_pages_v13_31.py`

## Verification

- `tests/test_v13_31_export_artifact_ux.py`

## Value

Operators can inspect generated export artifacts from the Full Dossier v2 surface, and the runtime acceptance scripts preserve the expected browser workflow.
