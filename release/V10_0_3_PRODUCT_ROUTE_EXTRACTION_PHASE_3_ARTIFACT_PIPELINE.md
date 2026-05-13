# v10.0.3 - Product Route Extraction Phase 3: Artifact Pipeline Split

## Purpose

v10.0.3 continues the v10 clean architecture split by introducing a dedicated artifact pipeline module for the v9.8.4-v9.8.9 artifact browser/review/audit/export/package surface while preserving all public URLs.

## Adds

- Dedicated artifact product module:
  - `src/socmint/product_artifacts.py`

- Safe migration module manifest:
  - `product_artifacts.product_artifacts_manifest`

- Compatibility-preserved route family:
  - Artifact Browser
  - Artifact Review / Pin / Archive controls
  - Artifact Review Audit Trail
  - Artifact Evidence Chain Export Manifest
  - Product Release Package Builder
  - Release Package ZIP Export + Download

- v10 architecture manifest update:
  - records `product_artifacts.product_artifacts_manifest`

- Smoke targets:
  - `make product-artifact-pipeline-extraction-smoke`
  - `make test1003`
  - `make artifact-pipeline-extraction-hardening-smoke`

## Compatibility Rule

No public artifact pipeline URL is changed or removed.

This phase is intentionally migration-safe:

- helpers are re-exported from `dashboard.py`
- public routes remain routable
- v10 architecture inventory records the artifact pipeline module
- the smoke test proves artifact browser, review, audit, export manifest, package builder, and ZIP export surfaces remain reachable

## Next Extraction Phase

Future v10 phases can move actual artifact blueprint ownership route-by-route after helper dependencies are reduced.
