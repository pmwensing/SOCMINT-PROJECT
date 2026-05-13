# v9.8.4 - Product Control Runtime History + Artifact Browser

## Adds

- Product artifact browser UI:
  - `/product/artifacts`

- Product artifact API:
  - `/api/v1/product/artifacts`

- Artifact view/download routes:
  - `/product/artifacts/view/{path}`
  - `/product/artifacts/download/{path}`

- Product Control Center runtime history panel.

- Product Artifacts navigation link.

- Smoke targets:
  - `make product-artifacts-smoke`
  - `make test984`
  - `make artifact-hardening-smoke`

## Scope

The artifact browser lists release and product QA artifacts from:

- `release/`
- `storage/product_qa/`

It provides browser view and download links for markdown, JSON, text, CSV, and HTML artifacts.
