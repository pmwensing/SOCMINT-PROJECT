# v9.9.0 - Product Release Candidate Console

## Adds

- Release Candidate Console:
  - `/product/release-candidate`

- Release Candidate API:
  - `GET /api/v1/product/release-candidate`
  - `POST /api/v1/product/release-candidate/write`

- RC manifest artifacts:
  - `release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json`
  - `release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.md`

- Hardening report:
  - `release/V9_9_0_RELEASE_CANDIDATE_HARDENING_REPORT.json`
  - `release/V9_9_0_RELEASE_CANDIDATE_HARDENING_REPORT.md`

- One-command RC smoke:
  - `make product-release-candidate-smoke`
  - `make test990`
  - `make release-candidate-hardening-smoke`

## Scope

The console verifies the full v9.8 product chain:

- Product smoke
- Artifact review
- Artifact review audit trail
- Evidence-chain export manifest
- Release package builder
- Release package ZIP export/download

## Purpose

v9.9.0 creates a single release candidate dashboard and manifest so the operator can verify product readiness before cutting a release candidate.
