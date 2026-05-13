# v10.0.1 - Product Route Extraction Phase 1

## Purpose

v10.0.1 begins the clean architecture split by moving the v9.9.0-v9.9.4 final release flow routes out of `dashboard.py` and into a dedicated product module while keeping every existing URL unchanged.

## Adds

- Dedicated extracted product release flow module:
  - `src/socmint/product_release_flow.py`

- Extracted blueprint:
  - `product_release_flow.product_release_flow_bp`

- Compatibility-preserved route family:
  - v9.9.0 Release Candidate Console
  - v9.9.1 Final Product Gate
  - v9.9.2 Final Release Publisher
  - v9.9.3 Final Release Archive + Integrity Seal
  - v9.9.4 Final Release Verification Console

- v10 architecture manifest update:
  - the v10 foundation manifest now records the extracted blueprint

- Smoke targets:
  - `make product-route-extraction-smoke`
  - `make test1001`
  - `make route-extraction-hardening-smoke`

## Compatibility Rule

No public v9.9.x final release URL is changed or removed.

The smoke proves:

- extracted routes are served by the new `product_release_flow` blueprint
- v9.9.x final release URLs still return HTTP 200
- v10 architecture compatibility remains clean
- the v10 architecture manifest still writes successfully

## Next Extraction Phases

Future v10 phases can extract:

- v9.9.5-v9.9.9 post-release/distribution/bootstrap routes
- artifact review/export/package routes
- product QA/report route helpers
