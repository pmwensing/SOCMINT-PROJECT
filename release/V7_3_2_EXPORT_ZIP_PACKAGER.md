
# SOCMINT v7.3.2 — Export ZIP Packager + Download Bundle

## Added

- ZIP bundle builder for review-gated exports
- Bundle download endpoint
- Bundle history panel in Export Center
- Bundle metadata:
  - name
  - size
  - modified time
  - download URL
- Audit snapshot inside each ZIP
- README inside each ZIP
- `make test732`

## Routes

- `POST /api/v1/reports/export-center/zip`
- `POST /reports/export-center/zip/run`
- `GET /reports/export-center/bundles/{name}/download`

## Validate

`make test732`
