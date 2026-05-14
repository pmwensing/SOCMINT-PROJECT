# SOCMINT v10.22.0 — Certification Index Compatibility Cleanup

## Summary

Adds compatibility aliases for the older export-certification-index route family while preserving the stronger canonical case-scoped certification index implementation already on master.

## Changes

- Keeps canonical certification index routes unchanged.
- Adds compatibility aliases under `/api/v1/dossier-builder/v3/export-certification-index/<case_id>`.
- Adds summary and review compatibility aliases.
- Marks compatibility responses with `compatibility_alias` and `canonical_route_family` metadata.
- Adds focused route registration tests.

## Canonical routes

- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/summary`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/markdown`
- `GET /api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>`

## Compatibility routes

- `GET /api/v1/dossier-builder/v3/export-certification-index/<case_id>`
- `GET /api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary`
- `GET /api/v1/dossier-builder/v3/export-certification-index/<case_id>/review`

## Merge gate

Full CI must pass before merge.
