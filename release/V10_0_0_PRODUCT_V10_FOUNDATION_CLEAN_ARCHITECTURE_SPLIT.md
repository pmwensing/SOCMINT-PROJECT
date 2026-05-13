# v10.0.0 - Product v10 Foundation + Clean Architecture Split

## Preconditions

v10.0.0 must only start after:

- v9.9.9 is tagged
- v9.9.9 is merged into master
- the v9.9.x closure and v10 bootstrap gate exists

The build script enforces the v9.9.9 tag and master ancestry before creating the v10 branch.

## Adds

- Dedicated v10 product module:
  - `src/socmint/product_v10.py`

- v10 product UI:
  - `/product/v10`
  - `/product/v10/bootstrap-compat`

- v10 product APIs:
  - `GET /api/v1/product/v10/architecture`
  - `POST /api/v1/product/v10/architecture/write`
  - `GET /api/v1/product/v10/compatibility`

- v10 architecture manifest:
  - `release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json`
  - `release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md`

- v10 hardening report:
  - `release/V10_0_0_PRODUCT_FOUNDATION_HARDENING_REPORT.json`
  - `release/V10_0_0_PRODUCT_FOUNDATION_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-v10-foundation-smoke`
  - `make test1000`
  - `make v10-foundation-hardening-smoke`

## Architecture Split Strategy

v10.0.0 starts the clean architecture split by creating a dedicated `product_v10` blueprint while leaving the v9.9.x final release routes in place as compatibility aliases.

This is intentionally migration-safe:

- no v9.9.x final release endpoint is removed
- the v10 blueprint exposes route inventory and compatibility status
- the smoke test proves v9.9.9 routes still respond after the v10 blueprint is registered

## Compatibility Policy

All v9.9.x final release endpoints remain routable until v10 replacement routes are stable and verified.
