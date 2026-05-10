# SOCMINT v7.5.1 — Full Report Alias + Export Manifest Hashing + UI Polish

## Added

- Full-report alias layer for the existing Full Entity Profile Dossier v2 engine.
- WSGI registration for the new full-report aliases.
- Export manifest generation for dossier bundles.
- SHA-256 hashing for exported dossier artifacts.
- `manifest_path`, `manifest`, and `full_report_download_url` in dossier export responses.
- `make test751` and `make zip751`.

## New alias routes

- `GET /api/v1/spine/subjects/{subject_id}/full-report`
- `POST /api/v1/spine/subjects/{subject_id}/full-report/run`
- `GET /api/v1/spine/subjects/{subject_id}/full-report/latest`
- `GET /api/v1/spine/subjects/{subject_id}/full-report/download?name={zip_name}`
- `POST /spine/subjects/{subject_id}/full-report/run`

## Existing dossier-v2 routes preserved

- `GET /api/v1/spine/subjects/{subject_id}/dossier-v2`
- `POST /api/v1/spine/subjects/{subject_id}/dossier-v2/export`
- `GET /spine/subjects/{subject_id}/dossier`
- `POST /spine/subjects/{subject_id}/dossier-v2/export/run`
- `GET /spine/subjects/{subject_id}/dossier-v2/export/{name}/download`

## Export manifest

Each v7.5.1 export now writes:

- JSON dossier
- Markdown dossier
- HTML dossier
- `*-export_manifest.json`
- ZIP bundle

The manifest records artifact role, filename, path, size, and SHA-256 digest.

## Validate

```bash
make test751
```
