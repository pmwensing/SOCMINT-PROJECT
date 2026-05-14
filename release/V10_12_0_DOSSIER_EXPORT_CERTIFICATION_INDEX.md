# SOCMINT v10.12.0 — Dossier Export Certification Index

## Summary

Adds a listable certification index across persisted dossier exports so operators can quickly see which exports are certified and which require review.

## Changes

- Adds certification index helper.
- Adds certification index summary helper.
- Adds certification review-items helper.
- Adds authenticated certification index routes.
- Registers certification index routes through the production release route module.
- Adds focused v10.12 certification index tests.

## Routes

- `GET /api/v1/dossier-builder/v3/export-certification-index`
- `GET /api/v1/dossier-builder/v3/export-certification-index/summary`
- `GET /api/v1/dossier-builder/v3/export-certification-index/review`

## Merge gate

Full CI must pass before merge.
