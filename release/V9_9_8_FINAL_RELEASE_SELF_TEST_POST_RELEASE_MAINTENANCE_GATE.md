# v9.9.8 - Final Release Self-Test + Post-Release Maintenance Gate

## Adds

- Final Self-Test UI:
  - `/product/final/self-test`

- Final Self-Test APIs:
  - `GET /api/v1/product/final/self-test`
  - `POST /api/v1/product/final/self-test/write`
  - `POST /api/v1/product/final/self-test/maintenance`
  - `GET /api/v1/product/final/self-test/maintenance-audit`

- Runtime state:
  - `storage/product_qa/post_release_maintenance_state.json`
  - `storage/product_qa/post_release_maintenance_audit.json`

- Post-release maintenance report:
  - `release/V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.json`
  - `release/V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.md`

- Hardening report:
  - `release/V9_9_8_FINAL_SELF_TEST_HARDENING_REPORT.json`
  - `release/V9_9_8_FINAL_SELF_TEST_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-final-self-test-smoke`
  - `make test998`
  - `make final-self-test-hardening-smoke`

## One-Page Self-Test Checks

The self-test verifies:

- v9.9.0 RC manifest is passing
- v9.9.1 final gate is approved
- v9.9.3 archive ZIP/TAR/integrity files exist
- v9.9.4 final verification is passing
- v9.9.5 distribution readiness is ready
- v9.9.6 final dashboard is ready
- v9.9.7 handoff is ready
- v9.9.7 handoff manifest exists and is ready

## v10 Gate Rule

The v10 maintenance/start gate is blocked unless:

- final self-test status is `pass`
- v9.9.7 handoff status is `ready`
- all final release chain checks pass

## Purpose

v9.9.8 gives the operator one post-release self-test page and an explicit safe-to-start-v10 maintenance gate.
