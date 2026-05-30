# v13.21 — Real-World Usability Smoke

## Purpose

Add a CI-visible route smoke test for the main analyst workflow created during v13.

## Added

- `tests/test_v13_21_usability_smoke.py`
  - Verifies the review queue, readiness UI/API, claim/evidence ledger UI/API, handoff status API, promotion API, update API, and manifest draft API are registered together.

## Covered routes

```text
/review/normalization-queue
/api/v1/review/normalization-queue
/api/v1/review/normalization-update
/api/v1/review/normalization-promote
/subjects/<subject_id>/dossier/readiness
/api/v1/subjects/<subject_id>/dossier/readiness
/subjects/<subject_id>/claim-evidence-ledger
/api/v1/subjects/<subject_id>/claim-evidence-ledger
/api/v1/subjects/<subject_id>/handoff-status
/api/v1/subjects/<subject_id>/export-manifest-draft
```

## Value

Future changes will fail CI if the core operator workflow routes disappear or stop registering.
