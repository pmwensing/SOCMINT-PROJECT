# v9.9.4 - Final Release Verification Console

## Adds

- Final Release Verification UI:
  - `/product/final-release/verify`

- Verification API:
  - `GET /api/v1/product/final-release/verify`
  - `GET /api/v1/product/final-release/verify?release_name={release_name}`

- Verification outputs:
  - `release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json`
  - `release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.md`

- Hardening outputs:
  - `release/V9_9_4_FINAL_RELEASE_VERIFY_HARDENING_REPORT.json`
  - `release/V9_9_4_FINAL_RELEASE_VERIFY_HARDENING_REPORT.md`

- Smoke targets:
  - `make product-final-release-verify-smoke`
  - `make test994`
  - `make final-release-verify-hardening-smoke`

## Verification Checks

The console verifies:

- archive ZIP/TAR files exist
- archive ZIP/TAR checksums match the integrity seal when available
- required final release files exist
- integrity manifest per-file SHA256 checks pass
- package ZIPs referenced in the publish manifest are present
- final gate is approved
- publish manifest status is `published`
- archives contain release notes, checklist, publish manifest, RC manifest, final gate manifest, sign-off audit, and package ZIPs

## Purpose

v9.9.4 gives the operator one final verification console before treating the release archive as sealed and ready.
