# v13.23 - Workflow Navigation Polish

## Purpose

Document the Command Center navigation polish that links the v13 analyst workflow from the active subject cards.

## Added

- Command Center subject-card links for:
  - Normalization review queue
  - Dossier readiness
  - Claim/evidence ledger
  - Export manifest draft
  - Full Dossier v2
- Label coverage for the core workflow actions shown to operators.

## Verification

- `tests/test_v13_23_workflow_navigation.py`

## Value

Operators can move from Command Center subject context into the review, readiness, ledger, manifest, and full dossier surfaces without manually assembling URLs.
