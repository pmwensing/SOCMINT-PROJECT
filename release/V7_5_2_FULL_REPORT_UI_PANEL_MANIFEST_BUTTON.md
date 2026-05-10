# SOCMINT v7.5.2 — Full Report UI Button + Latest Export Panel + Manifest Download Button

## Added

- Full Entity Profile Dossier v2 page now includes a visible **Run Full Report** button.
- Latest Full Report Export panel on the dossier page.
- Download buttons for:
  - ZIP bundle
  - export manifest
  - HTML dossier
- Manifest table in the UI with artifact role, filename, size, and SHA-256 digest.
- `latest_full_report_export(subject_id)` helper for UI/API metadata.
- Context processor registration for latest full-report export metadata.
- `make test752` and `make zip752`.

## Hardened

- The visible **Run Full Report** button posts to the existing dossier-v2 export route so legacy dashboard rendering remains safe.
- The latest-export panel only renders download links when a latest export is available.

## Validate

```bash
make test752
```

## Expected UI

On `/spine/subjects/{subject_id}/dossier` analysts should see:

- Export dossier ZIP
- Run Full Report
- Latest Full Report Export
- Download ZIP
- Download Manifest
- Download HTML
- SHA-256 manifest table
