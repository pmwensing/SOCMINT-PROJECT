# v9.9.2 - Final Release Publisher + Release Notes Pack

## Adds

- Final Release Publisher UI:
  - `/product/final-release`

- Final Release API:
  - `GET /api/v1/product/final-release`
  - `POST /api/v1/product/final-release/publish`

- Final release output directory:
  - `storage/final_releases/{release_name}/RELEASE_NOTES.md`
  - `storage/final_releases/{release_name}/FINAL_RELEASE_CHECKLIST.json`
  - `storage/final_releases/{release_name}/PUBLISH_MANIFEST.json`
  - copied RC/final gate manifests
  - copied sign-off state and audit
  - copied release package ZIPs

- Latest release artifacts:
  - `release/V9_9_2_FINAL_RELEASE_NOTES.md`
  - `release/V9_9_2_FINAL_RELEASE_CHECKLIST.json`
  - `release/V9_9_2_FINAL_RELEASE_PUBLISH_MANIFEST.json`

- Hardening report:
  - `release/V9_9_2_FINAL_RELEASE_HARDENING_REPORT.json`
  - `release/V9_9_2_FINAL_RELEASE_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-final-release-smoke`
  - `make test992`
  - `make final-release-hardening-smoke`

## Gate Rule

Final release publish is blocked unless the final product gate is approved and the RC chain status is pass.

## Purpose

v9.9.2 converts the signed-off release candidate into a final release notes pack with checklist, publish manifest, and packaged release evidence.
