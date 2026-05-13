# v9.8.7 - Product Artifact Evidence Chain + Export Manifest

## Adds

- Evidence-chain export manifest for reviewed or important artifacts.
- API:
  - `GET /api/v1/product/artifact-export-manifest`
  - `GET /api/v1/product/artifact-export-manifest?include_archived=true`
  - `POST /api/v1/product/artifact-export-manifest/write`
- UI:
  - `/product/artifacts/export-manifest`
  - one-click write action from the export manifest page
  - artifact browser export panel
  - Product Control export panel
- Written artifacts:
  - `release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.json`
  - `release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.md`
- Manifest includes:
  - artifact path/kind/size/modified time
  - selection reason
  - review state
  - audit summary
  - view/download/audit links
- Smoke targets:
  - `make product-artifact-export-manifest-smoke`
  - `make test987`
  - `make export-manifest-hardening-smoke`

## Purpose

v9.8.7 turns reviewed and important product artifacts into an exportable evidence chain with review state and audit summaries suitable for release package handoff.
