# v9.8.9 - Product Release Package ZIP Export + Download

## Adds

- Package inventory API:
  - `GET /api/v1/product/release-packages`

- Package ZIP API:
  - `POST /api/v1/product/release-package/{package_name}/zip`

- Package ZIP download:
  - `GET /product/release-package/download/{package_name}`

- UI:
  - Built Packages + ZIP Export panel on `/product/release-package`
  - Release Package ZIP Export panel on Product Control

- ZIP validates:
  - `PACKAGE_MANIFEST.json`
  - `PACKAGE_INDEX.md`
  - selected reviewed/important artifacts only
  - review metadata
  - review audit log

- Smoke targets:
  - `make product-release-package-zip-smoke`
  - `make test989`
  - `make release-package-zip-hardening-smoke`

## Purpose

v9.8.9 turns the v9.8.8 package directory into a downloadable ZIP release artifact and verifies package contents only include selected reviewed/important artifacts plus required metadata and audit history.
