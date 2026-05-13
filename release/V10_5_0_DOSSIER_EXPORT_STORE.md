# SOCMINT v10.5.0 — Dossier Export Store

## Summary

Adds persisted dossier export storage for deterministic JSON/HTML dossier export packs.

## Changes

- Adds dossier export store helpers.
- Persists JSON and HTML dossier artifacts under `exports/dossiers`.
- Adds per-subject/case manifest generation.
- Adds manifest loading and export-store summary helpers.
- Adds export-store API routes.
- Registers export-store routes through the production release route module.
- Adds focused v10.5 export-store tests.

## Routes

- `POST /api/v1/dossier-builder/v3/export-store`
- `GET /api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/manifest`
- `GET /api/v1/dossier-builder/v3/export-store/<case_id>/<subject_id>/summary`

## Merge gate

Full CI must pass before merge.
