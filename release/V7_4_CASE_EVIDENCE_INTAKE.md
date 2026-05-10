
# SOCMINT v7.4 — Case Evidence Intake + Export Attachment Builder

## Added

- Case Evidence Intake page
- Local evidence copy/storage under `var/socmint/evidence/`
- SHA-256 hashing for each stored evidence file
- Evidence manifest `EVIDENCE-MANIFEST.json`
- Evidence download route
- Export attachment manifest builder
- Export attachment ZIP builder
- Attachment ZIP includes:
  - attachment manifest
  - evidence files
  - README
- `make test74`

## Routes

- `GET /evidence/intake`
- `GET /api/v1/evidence/intake`
- `POST /api/v1/evidence/intake`
- `POST /evidence/intake/add`
- `GET /evidence/intake/files/{name}/download`
- `POST /api/v1/reports/export-center/attachments`
- `POST /api/v1/reports/export-center/attachments/zip`

## Validate

`make test74`
