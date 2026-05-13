# v9.9.1 - Release Candidate Sign-Off + Final Product Gate

## Adds

- Final Product Gate UI:
  - `/product/final-gate`

- Final Product Gate API:
  - `GET /api/v1/product/final-gate`
  - `POST /api/v1/product/final-gate/write`
  - `POST /api/v1/product/final-gate/signoff`
  - `GET /api/v1/product/final-gate/signoff-audit`

- Sign-off state:
  - `storage/product_qa/release_candidate_signoff_state.json`

- Append-only sign-off audit:
  - `storage/product_qa/release_candidate_signoff_audit.json`

- Final gate manifest:
  - `release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json`
  - `release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.md`

- Hardening report:
  - `release/V9_9_1_FINAL_PRODUCT_GATE_HARDENING_REPORT.json`
  - `release/V9_9_1_FINAL_PRODUCT_GATE_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-final-gate-smoke`
  - `make test991`
  - `make final-gate-hardening-smoke`

## Gate Rules

- Approval is denied unless the v9.9.0 RC chain status is `pass`.
- Operator can approve, block, or reset the gate.
- Every sign-off attempt is written to an append-only audit log.
- Final gate manifest records RC status, sign-off decision, audit count, and recommended next action.

## Purpose

v9.9.1 creates the final accountable release gate before cutting a final product release.
