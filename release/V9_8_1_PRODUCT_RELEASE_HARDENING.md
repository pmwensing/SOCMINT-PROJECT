# v9.8.1 — Product Release Hardening + Route/UI Wiring

## Adds

- Product Build Control Center UI route:
  - `/product/build-control`

- Product API route wiring:
  - `/api/v1/product/build-status`
  - `/api/v1/product/release-readiness`
  - `/api/v1/product/smoke-summary`
  - `/api/v1/product/system-health`
  - `/api/v1/product/write-reports`

- Dossier QA route wiring:
  - `/api/v1/dossier/{subject_id}/quality-gate`
  - `/api/v1/dossier/{subject_id}/traceability`

- Route smoke:
  - `make product-route-smoke`
  - `make test981`

- Full hardening smoke:
  - `make release-hardening-smoke`

## Purpose

v9.8.1 verifies that the v9.7 product-control capabilities are not only importable, but exposed through the operator app and reachable through authenticated Flask route smoke tests.
