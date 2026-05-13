# v9.9.5 - Final Release Lock + Distribution Readiness

## Adds

- Distribution Readiness UI:
  - `/product/final-release/distribution`

- Distribution APIs:
  - `GET /api/v1/product/final-release/distribution`
  - `POST /api/v1/product/final-release/distribution/write`
  - `POST /api/v1/product/final-release/distribution/decision`
  - `GET /api/v1/product/final-release/distribution/audit`

- Runtime state:
  - `storage/product_qa/final_release_distribution_state.json`
  - `storage/product_qa/final_release_distribution_audit.json`

- Distribution readiness report:
  - `release/V9_9_5_DISTRIBUTION_READINESS_REPORT.json`
  - `release/V9_9_5_DISTRIBUTION_READINESS_REPORT.md`

- Hardening report:
  - `release/V9_9_5_DISTRIBUTION_READINESS_HARDENING_REPORT.json`
  - `release/V9_9_5_DISTRIBUTION_READINESS_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-distribution-readiness-smoke`
  - `make test995`
  - `make distribution-readiness-hardening-smoke`

## Rules

- Distribution cannot be locked or marked ready unless final release verification status is `pass`.
- Lock stores the SHA256 of the v9.9.4 verification report.
- Marking ready freezes a verified final release state as ready to distribute.
- Every lock/ready/block/reset attempt writes an audit event.

## Purpose

v9.9.5 gives the operator a final distribution gate after archive verification, preventing accidental release of unverified builds.
