# v9.8.8 - Product Release Package Builder

## Adds

- Release package builder UI:
  - `/product/release-package`

- Release package API:
  - `GET /api/v1/product/release-package`
  - `POST /api/v1/product/release-package/build`

- Release package output:
  - `storage/product_packages/{package_name}/PACKAGE_MANIFEST.json`
  - `storage/product_packages/{package_name}/PACKAGE_INDEX.md`
  - copied reviewed/important selected artifacts
  - copied export manifest JSON/MD
  - copied review metadata
  - copied audit log

- Latest release artifacts:
  - `release/V9_8_8_PRODUCT_RELEASE_PACKAGE_MANIFEST.json`
  - `release/V9_8_8_PRODUCT_RELEASE_PACKAGE_INDEX.md`

- Smoke targets:
  - `make product-release-package-smoke`
  - `make test988`
  - `make release-package-hardening-smoke`

## Purpose

v9.8.8 turns the reviewed/important artifact evidence chain into a portable release package directory with selected artifacts, manifests, review metadata, and audit history.
