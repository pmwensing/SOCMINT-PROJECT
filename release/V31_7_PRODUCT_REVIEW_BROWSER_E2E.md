# v31.7 — Product Review and Browser E2E

## Objective

Validate the complete v31 publication workflow, required modules, assets, routes, and administrator-facing browser journey.

## Delivered

- Publication Product Review checkpoint
- module and asset inventory
- required-route checks
- duplicate route detection
- unexpected migration detection
- seven-step workflow inventory
- administrator-only UI and API
- headless Chrome browser E2E with ten checks
- focused checkpoint, route, and browser-contract tests

## Routes

- `GET /publication-review/product-review`
- `GET /api/v1/publication-review/product-review-checkpoint`

## Browser checks

- workspace page
- product-review page
- workspace API
- candidates API
- draft revisions API
- editorial validations API
- release approvals API
- published revisions API
- supersessions API
- ready checkpoint

## Validation

Focused tests, v31 regression tests, the full suite, Ruff, browser E2E, CI, and verification workflows are required.

## Safety

- no publication workflow mutation
- no external transmission
- no database migration

## Next action

Run all validation gates and finalize v31 status.
