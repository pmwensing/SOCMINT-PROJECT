# v9.8.3 - Product Control Runtime Actions

## Adds

- Runtime action panel in Product Build Control Center
- UI POST actions:
  - `/product/actions/refresh-readiness`
  - `/product/actions/write-reports`
  - `/product/actions/export-control-snapshot`

- API runtime actions:
  - `GET /api/v1/product/runtime-actions`
  - `POST /api/v1/product/actions/write-reports`
  - `POST /api/v1/product/actions/export-control-snapshot`

- Runtime snapshot artifacts:
  - `release/V9_8_3_PRODUCT_CONTROL_RUNTIME_SNAPSHOT.json`
  - `release/V9_8_3_PRODUCT_CONTROL_RUNTIME_SNAPSHOT.md`

- Smoke targets:
  - `make product-runtime-actions-smoke`
  - `make test983`
  - `make runtime-hardening-smoke`

## Purpose

v9.8.3 makes the Product Build Control Center operational by adding authenticated runtime actions for report generation, readiness refresh, and exportable product-control snapshots.
