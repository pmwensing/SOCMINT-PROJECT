
# SOCMINT v7.3.1 — Export Artifact Download Links + Manifest Viewer

## Added

- Manifest viewer page
- Safe artifact download endpoint
- JSON artifact API view
- Export Center artifact browser
- Path traversal guard for artifact access
- Artifact metadata:
  - name
  - size
  - modified time
  - view URL
  - download URL
- `make test731`

## Routes

- `/reports/export-center/manifests/{name}`
- `/api/v1/reports/export-center/artifacts/{name}`
- `/reports/export-center/artifacts/{name}/download`

## Validate

`make test731`
