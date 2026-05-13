# SOCMINT v10.3.0 — Full Entity Profile Dossier Builder v3

## Summary

Adds a deterministic dossier builder v3 layer for case-scoped entity profile packaging.

## Changes

- Adds dossier builder v3 core payload builder.
- Adds confidence scoring helper.
- Adds source traceability and evidence matrix output.
- Adds analyst review queue output.
- Adds export preflight readiness output.
- Adds dossier builder v3 API routes.
- Registers dossier builder routes through the production release route module.
- Adds focused v10.3 dossier builder tests.

## Routes

- `GET /api/v1/dossier-builder/v3/capabilities`
- `POST /api/v1/dossier-builder/v3/build`
- `POST /api/v1/dossier-builder/v3/summary`

## Merge gate

Full CI must pass before merge.
