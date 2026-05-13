# v9.9.6 - Final Product Release Dashboard + Version Freeze

## Adds

- Final Product Dashboard:
  - `/product/final`

- Final Product APIs:
  - `GET /api/v1/product/final`
  - `GET /api/v1/product/final?release_name={release_name}`
  - `POST /api/v1/product/final/write`

- Final product release artifacts:
  - `release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.json`
  - `release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.md`
  - `release/V9_9_6_FINAL_PRODUCT_VERSION_FREEZE.json`

- Hardening report:
  - `release/V9_9_6_FINAL_PRODUCT_DASHBOARD_HARDENING_REPORT.json`
  - `release/V9_9_6_FINAL_PRODUCT_DASHBOARD_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-final-dashboard-smoke`
  - `make test996`
  - `make final-product-dashboard-hardening-smoke`

## Dashboard Stages

The final dashboard shows:

- Release Candidate status
- Final Gate status
- Archive status
- Verification status
- Distribution readiness status
- Frozen final version/release line

## Version Freeze

The visible final product release line is frozen as:

- Product: SOCMINT Workbench
- Final version: v9.9.6
- Release line: v9.9.x final product release line

## Purpose

v9.9.6 provides a single operator-facing final product dashboard after distribution readiness, making the final release state obvious and preserving the release version freeze.
