# v9.8.5 - Product Artifact Review + Pin/Archive Controls

## Adds

- Artifact review metadata sidecar:
  - `storage/product_qa/product_artifact_metadata.json`

- Review controls:
  - reviewed
  - important
  - archived
  - note
  - reviewed_by
  - reviewed_at

- API endpoints:
  - `GET /api/v1/product/artifact-review-state`
  - `POST /api/v1/product/artifacts/review`

- UI controls:
  - `POST /product/artifacts/review`
  - review checkboxes on `/product/artifacts`
  - filters for reviewed, unreviewed, important, archived, active

- Smoke targets:
  - `make product-artifact-review-smoke`
  - `make test985`
  - `make artifact-review-hardening-smoke`

## Purpose

v9.8.5 turns the artifact browser into an operator review queue where generated release artifacts, QA reports, and snapshots can be marked reviewed, pinned as important, or archived.
