# v9.8.2 - Product Control Center Navigation + Operator UX Polish

## Adds

- Header navigation links:
  - Product Control
  - Operator Runbook

- Dashboard readiness card:
  - release-readiness status
  - blocker/warning counts
  - links into product control workflow

- Product Build Control Center action panel:
  - product smoke command
  - route smoke command
  - release hardening command
  - dossier quality gate link
  - dossier traceability link

- Operator Runbook page:
  - `/product/operator-runbook`
  - `/api/v1/product/operator-runbook`

- UX smoke:
  - `make product-ux-smoke`
  - `make test982`

- Full UX hardening smoke:
  - `make ux-hardening-smoke`

## Purpose

v9.8.2 turns the v9.8.1 route wiring into a visible operator workflow so the product readiness loop is reachable from the main dashboard and the Product Build Control Center.
