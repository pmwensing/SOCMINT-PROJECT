# SOCMINT v10.6.0 — Dossier Download + Export Index

## Summary

Adds a listable export index and safe download resolver for persisted dossier export artifacts.

## Changes

- Adds dossier export index helpers.
- Lists persisted dossier export manifests.
- Adds per-case/per-subject export entry lookup.
- Adds safe download path resolution for allowed export files.
- Adds authenticated export index and download routes.
- Registers export index routes through the production release route module.
- Adds focused v10.6 export index tests.

## Routes

- `GET /api/v1/dossier-builder/v3/export-index`
- `GET /api/v1/dossier-builder/v3/export-index/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/export-download/<case_id>/<subject_id>/<filename>`

## Merge gate

Full CI must pass before merge.
