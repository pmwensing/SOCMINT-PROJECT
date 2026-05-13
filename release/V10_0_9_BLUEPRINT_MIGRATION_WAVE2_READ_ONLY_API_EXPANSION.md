# v10.0.9 - Blueprint Migration Wave 2: Read-Only API Expansion

## Purpose

v10.0.9 moves additional low/medium-risk GET API routes from the v10 migration plan into extracted blueprints.

## Wave 2 Moves

### `socmint.product_release_flow`

- `GET /api/v1/product/final-release`

### `socmint.product_post_release`

- No fallback-backed post-release API routes moved in this wave.

### `socmint.product_artifacts`

- `GET /api/v1/product/artifact-review-state`
- `GET /api/v1/product/artifact-review-audit`
- `GET /api/v1/product/artifact-export-manifest`
- `GET /api/v1/product/release-packages`

## Explicitly Blocked

This wave does not move:

- POST routes
- write routes
- build routes
- download routes
- archive creation routes
- publish/decision/signoff routes

## Adds

- Wave 2 UI:
  - `/product/v10/blueprint-wave2`

- Wave 2 APIs:
  - `GET /api/v1/product/v10/blueprint-wave2`
  - `POST /api/v1/product/v10/blueprint-wave2/write`

- Reports:
  - `release/V10_0_9_BLUEPRINT_WAVE2_REPORT.json`
  - `release/V10_0_9_BLUEPRINT_WAVE2_REPORT.md`
  - `release/V10_0_9_BLUEPRINT_WAVE2_HARDENING_REPORT.json`
  - `release/V10_0_9_BLUEPRINT_WAVE2_HARDENING_REPORT.md`

## Smoke Proof

The smoke proves:

- Wave 1 guardrails remain stable
- Wave 2 routes have blueprint-owned primary endpoints
- Wave 2 routes retain dashboard fallback routes
- Wave 2 routes return HTTP 200
- no blocked action/download/archive/build/write routes were moved
