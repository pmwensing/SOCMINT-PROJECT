# SOCMINT v10.7.0 — Dossier Export Audit Trail

## Summary

Adds a deterministic audit trail for persisted dossier export workflows.

## Changes

- Adds dossier export audit helpers.
- Writes per-case/per-subject JSONL audit events.
- Adds audit summary and index helpers.
- Adds authenticated audit API routes.
- Registers audit routes through the production release route module.
- Adds focused v10.7 audit tests.

## Routes

- `GET /api/v1/dossier-builder/v3/export-audit`
- `GET /api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/summary`
- `POST /api/v1/dossier-builder/v3/export-audit/<case_id>/<subject_id>/event`

## Merge gate

Full CI must pass before merge.
