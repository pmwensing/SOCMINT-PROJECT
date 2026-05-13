# v10.0.8 - Blueprint Migration Wave 1 Guardrails + Rollback Console

## Purpose

v10.0.8 adds a guardrails and rollback-readiness console for the v10.0.7 Wave 1 blueprint migration.

## Adds

- Guardrails UI:
  - `/product/v10/blueprint-guardrails`

- Guardrails APIs:
  - `GET /api/v1/product/v10/blueprint-guardrails`
  - `POST /api/v1/product/v10/blueprint-guardrails/write`

- Guardrails report:
  - `release/V10_0_8_BLUEPRINT_GUARDRAILS_REPORT.json`
  - `release/V10_0_8_BLUEPRINT_GUARDRAILS_REPORT.md`

- Hardening report:
  - `release/V10_0_8_BLUEPRINT_GUARDRAILS_HARDENING_REPORT.json`
  - `release/V10_0_8_BLUEPRINT_GUARDRAILS_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-blueprint-guardrails-smoke`
  - `make test1008`
  - `make blueprint-guardrails-hardening-smoke`

## Guardrails

Every moved Wave 1 route must have:

- blueprint-owned primary endpoint
- dashboard fallback route
- HTTP 200 response
- no POST/write/build/download/archive/publish/decision/signoff route movement
- route ownership map consistency

## Rollback Rule

Wave 1 is rollback-ready only if every moved route has both:

- a blueprint primary route
- a dashboard fallback route
