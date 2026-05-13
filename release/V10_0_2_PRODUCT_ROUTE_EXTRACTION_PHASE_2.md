# v10.0.2 - Product Route Extraction Phase 2

## Purpose

v10.0.2 continues the v10 clean architecture split by introducing a dedicated post-release module for the v9.9.5-v9.9.9 workflow while preserving all public URLs.

## Adds

- Dedicated post-release product module:
  - `src/socmint/product_post_release.py`

- Safe migration module manifest:
  - `product_post_release.product_post_release_manifest`

- Compatibility-preserved route family:
  - v9.9.5 Distribution Readiness
  - v9.9.6 Final Product Dashboard
  - v9.9.7 Operator Handoff
  - v9.9.8 Final Self-Test + Maintenance Gate
  - v9.9.9 v10 Bootstrap Gate

- v10 architecture manifest update:
  - records `product_post_release.product_post_release_manifest`

- Smoke targets:
  - `make product-post-release-extraction-smoke`
  - `make test1002`
  - `make post-release-extraction-hardening-smoke`

## Compatibility Rule

No public v9.9.x final release or post-release URL is changed or removed.

This phase is intentionally migration-safe:

- helpers are re-exported from `dashboard.py`
- public routes remain routable
- v10 architecture inventory records the post-release module
- the smoke test exercises distribution, handoff, self-test, and v10-bootstrap routes

## Next Extraction Phase

Future v10 phases can move actual blueprint ownership route-by-route after helper dependencies are reduced.
