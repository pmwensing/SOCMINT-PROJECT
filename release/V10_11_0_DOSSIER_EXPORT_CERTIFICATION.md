# SOCMINT v10.11.0 — Dossier Export Certification Bundle

## Summary

Adds a compact dossier export certification bundle that combines gate decision, verification status, audit counts, and artifact digest metadata.

## Changes

- Adds artifact digest summary helper.
- Adds export certification bundle helper.
- Adds export certification summary helper.
- Adds export certification statement helper.
- Adds authenticated export certification routes.
- Registers certification routes through the production release route module.
- Adds focused v10.11 certification tests.

## Routes

- `GET /api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/summary`
- `GET /api/v1/dossier-builder/v3/export-certification/<case_id>/<subject_id>/statement`

## Merge gate

Full CI must pass before merge.
