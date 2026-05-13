# v10.0.7 - Blueprint Migration Wave 1: Low-Risk Read-Only Routes

## Purpose

v10.0.7 performs the first real blueprint ownership handoff for low-risk GET/read-only routes while preserving every public URL.

## Moves to Blueprint Ownership

### `socmint.product_release_flow`

- `GET /product/release-candidate`
- `GET /api/v1/product/release-candidate`
- `GET /product/final-gate`
- `GET /api/v1/product/final-gate`

### `socmint.product_post_release`

- `GET /product/final`
- `GET /api/v1/product/final`
- `GET /product/final/handoff`
- `GET /api/v1/product/final/handoff`
- `GET /product/final/self-test`
- `GET /api/v1/product/final/self-test`
- `GET /product/final/v10-bootstrap`
- `GET /api/v1/product/final/v10-bootstrap`

### `socmint.product_artifacts`

- `GET /product/artifacts`
- `GET /api/v1/product/artifacts`
- `GET /product/release-package`
- `GET /api/v1/product/release-package`

## Safety Controls

- Dashboard fallback routes remain registered.
- Extracted blueprints are registered before dashboard fallback routes.
- Public URLs remain unchanged.
- Only GET/read-only first-wave routes move.
- No POST/write/build/download/archive/action routes move in this wave.

## Smoke Proof

The v10.0.7 smoke proves:

- moved routes return HTTP 200
- first matching endpoint is blueprint-owned
- dashboard fallback route still exists
- route ownership map marks moved routes as `blueprint-owned`
- module health remains healthy
