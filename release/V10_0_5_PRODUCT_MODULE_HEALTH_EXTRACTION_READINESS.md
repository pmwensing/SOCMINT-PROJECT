# v10.0.5 - Product Module Health Console + Extraction Readiness Score

## Purpose

v10.0.5 adds a module health console and extraction readiness score before deeper blueprint ownership migration.

## Adds

- Module Health UI:
  - `/product/v10/module-health`

- Module Health APIs:
  - `GET /api/v1/product/v10/module-health`
  - `POST /api/v1/product/v10/module-health/write`

- Readiness artifacts:
  - `release/V10_0_5_MODULE_HEALTH_READINESS_REPORT.json`
  - `release/V10_0_5_MODULE_HEALTH_READINESS_REPORT.md`

- Hardening report:
  - `release/V10_0_5_MODULE_HEALTH_HARDENING_REPORT.json`
  - `release/V10_0_5_MODULE_HEALTH_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-module-health-smoke`
  - `make test1005`
  - `make module-health-hardening-smoke`

## Health Score Inputs

Each module receives a weighted readiness score:

- route presence: 40%
- helper export count: 25%
- smoke target availability: 25%
- registry ownership consistency: 10%

## Modules Scored

- `socmint.product_release_flow`
- `socmint.product_post_release`
- `socmint.product_artifacts`
- `socmint.product_registry`

## Readiness Rule

Deeper blueprint extraction is allowed only when every module is healthy and has all expected compatibility routes/smoke targets present.
