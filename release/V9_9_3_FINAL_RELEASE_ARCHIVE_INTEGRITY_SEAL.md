# v9.9.3 - Final Release Archive + Integrity Seal

## Adds

- Final Release Archive UI:
  - `/product/final-release/archive`

- Archive APIs:
  - `GET /api/v1/product/final-release/archives`
  - `GET /api/v1/product/final-release/archive/{release_name}`
  - `POST /api/v1/product/final-release/archive/{release_name}/create`
  - `GET /product/final-release/archive/download/{release_name}.zip`
  - `GET /product/final-release/archive/download/{release_name}.tar.gz`

- Archive outputs:
  - `storage/final_release_archives/{release_name}.zip`
  - `storage/final_release_archives/{release_name}.tar.gz`

- Integrity outputs:
  - `{release_pack}/INTEGRITY_MANIFEST.json`
  - `release/V9_9_3_FINAL_RELEASE_INTEGRITY_MANIFEST.json`
  - `release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.json`
  - `release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.md`

- Smoke targets:
  - `make product-final-release-archive-smoke`
  - `make test993`
  - `make final-release-archive-hardening-smoke`

## Required Evidence Verified

The archive smoke proves the final archive contains:

- release notes
- final checklist
- publish manifest
- RC manifest
- final gate manifest
- sign-off audit
- package ZIPs
- integrity manifest

## Purpose

v9.9.3 seals the final release notes pack with downloadable ZIP/TAR archives and SHA256 integrity evidence.
