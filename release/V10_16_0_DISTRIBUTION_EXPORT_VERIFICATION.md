# SOCMINT v10.16.0 — Distribution Export Verification + Integrity Console

## Summary

Adds an integrity verification layer for generated distribution ZIP exports. The verifier checks required ZIP contents, ZIP hash and size, manifest consistency, artifact counts, and source file hashes.

## Focus

The integrity console answers:

- Does the distribution ZIP still match the export manifest?
- Are all required files present?
- Are artifact counts consistent?
- Do source files still match recorded hashes?
- Is the export safe to rely on after build?

## Changes

- Adds `src/socmint/distribution_export_verification.py`.
- Adds `src/socmint/distribution_export_verification_routes.py`.
- Registers routes in `src/socmint/wsgi.py`.
- Adds verification links to `src/socmint/templates/certification_dashboard.html`.
- Adds `tests/test_distribution_export_verification_v10_16.py`.
- Adds `scripts/test_v10_16.sh`.

## Routes

- `GET /api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify`
- `GET /api/v1/dossier-builder/v3/distribution-export/<case_id>/<subject_id>/verify/markdown`

## Verification checks

- Distribution export manifest exists.
- ZIP exists.
- ZIP SHA-256 matches manifest.
- ZIP size matches manifest.
- Required files exist inside the ZIP.
- Artifact count in ZIP matches manifest.
- Source files still exist.
- Source file hashes still match manifest.

## Merge gate

Run:

```bash
bash scripts/test_v10_16.sh
```

or:

```bash
PYTHONPATH=src pytest -q tests/test_distribution_export_verification_v10_16.py tests/test_distribution_packet_export_v10_15.py tests/test_distribution_actions_v10_14.py tests/test_certification_dashboard_v10_13.py tests/test_dossier_certification_index_v10_12.py
```
