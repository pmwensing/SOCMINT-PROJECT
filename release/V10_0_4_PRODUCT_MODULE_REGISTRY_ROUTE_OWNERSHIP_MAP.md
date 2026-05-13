# v10.0.4 - Product Module Registry + Route Ownership Map

## Purpose

v10.0.4 adds a central product module registry and route ownership map for the v10 clean architecture split.

## Adds

- Product registry module:
  - `src/socmint/product_registry.py`

- Product registry UI:
  - `/product/v10/modules`

- Product registry APIs:
  - `GET /api/v1/product/v10/modules`
  - `POST /api/v1/product/v10/modules/write`
  - `GET /api/v1/product/v10/route-ownership`

- Registry artifacts:
  - `release/V10_0_4_PRODUCT_MODULE_REGISTRY.json`
  - `release/V10_0_4_PRODUCT_MODULE_REGISTRY.md`

- Hardening report:
  - `release/V10_0_4_PRODUCT_MODULE_REGISTRY_HARDENING_REPORT.json`
  - `release/V10_0_4_PRODUCT_MODULE_REGISTRY_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-module-registry-smoke`
  - `make test1004`
  - `make module-registry-hardening-smoke`

## Registered Extracted Modules

- `socmint.product_release_flow`
- `socmint.product_post_release`
- `socmint.product_artifacts`

## Ownership Types

- `dashboard-owned`: public route remains owned by `dashboard.py`
- `extracted-module-reexport`: helper surface is exposed from a dedicated v10 module while URLs remain compatibility-preserved

## Compatibility Rule

All v10.0.1, v10.0.2, and v10.0.3 compatibility routes must remain present.
