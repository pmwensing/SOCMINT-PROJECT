# v9.9.7 - Product Release Closeout + Operator Handoff Pack

## Adds

- Operator Handoff UI:
  - `/product/final/handoff`

- Operator Handoff APIs:
  - `GET /api/v1/product/final/handoff`
  - `POST /api/v1/product/final/handoff/build`

- Handoff pack output:
  - `storage/final_handoff/{handoff_name}/HANDOFF_MANIFEST.json`
  - `storage/final_handoff/{handoff_name}/PRINTABLE_HANDOFF_CHECKLIST.md`
  - `storage/final_handoff/{handoff_name}/README.md`
  - copied final release artifacts under `artifacts/{version}/`

- Latest release artifacts:
  - `release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json`
  - `release/V9_9_7_PRINTABLE_HANDOFF_CHECKLIST.md`
  - `release/V9_9_7_PRODUCT_RELEASE_CLOSEOUT_OPERATOR_HANDOFF.md`

- Hardening report:
  - `release/V9_9_7_OPERATOR_HANDOFF_HARDENING_REPORT.json`
  - `release/V9_9_7_OPERATOR_HANDOFF_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-operator-handoff-smoke`
  - `make test997`
  - `make operator-handoff-hardening-smoke`

## Included Release Chain

The handoff pack requires and copies artifacts from:

- v9.9.0 Release Candidate Manifest
- v9.9.1 Final Product Gate
- v9.9.2 Final Release Notes / Publish Manifest
- v9.9.3 Archive Seal / Integrity Manifest
- v9.9.4 Final Release Verification
- v9.9.5 Distribution Readiness
- v9.9.6 Final Product Dashboard / Version Freeze

## Purpose

v9.9.7 closes the product release workflow by generating a printable operator handoff checklist and collecting every final-release artifact needed for handoff.
