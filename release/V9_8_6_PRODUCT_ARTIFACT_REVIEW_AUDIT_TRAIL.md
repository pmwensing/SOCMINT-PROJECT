# v9.8.6 - Product Artifact Review Audit Trail

## Adds

- Append-only artifact review audit log:
  - `storage/product_qa/product_artifact_review_audit.json`

- Audit event fields:
  - event_id
  - action
  - artifact path
  - actor
  - timestamp
  - before state
  - after state
  - changed fields

- API endpoints:
  - `GET /api/v1/product/artifact-review-audit`
  - `GET /api/v1/product/artifact-review-audit?path={artifact_path}`

- UI:
  - `/product/artifacts/audit/{artifact_path}`
  - per-artifact audit links in artifact browser
  - review audit panel in Product Build Control Center

- Smoke targets:
  - `make product-artifact-review-audit-smoke`
  - `make test986`
  - `make artifact-review-audit-hardening-smoke`

## Purpose

v9.8.6 makes artifact review decisions accountable by preserving who changed reviewed, important, archived, or note fields, including before/after values and timestamped event history.
