# SOCMINT v10.9.0 — Dossier Export Verification Pack

## Summary

Adds verification reports for persisted dossier export artifacts.

## Changes

- Adds SHA-256 re-verification for stored export artifacts.
- Adds manifest/index consistency checks.
- Adds audit coverage checks.
- Adds full export verification report and summary helpers.
- Adds authenticated export verification routes.
- Registers verification routes through the production release route module.
- Adds focused v10.9 verification tests.

## Routes

- `GET /api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/summary`
- `GET /api/v1/dossier-builder/v3/export-verify/<case_id>/<subject_id>/hashes`

## Merge gate

Full CI must pass before merge.
