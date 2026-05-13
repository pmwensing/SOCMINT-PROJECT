# SOCMINT v10.10.0 — Dossier Export Verification Gate

## Summary

Adds a gate layer that converts dossier export verification reports into allow/deny readiness decisions.

## Changes

- Adds dossier export gate report helper.
- Adds dossier export gate summary helper.
- Adds dossier export gate decision helper.
- Adds authenticated gate routes.
- Registers gate routes through the production release route module.
- Adds focused v10.10 gate tests.

## Gate checks

- Artifact SHA-256 verification must pass.
- Manifest/index consistency must pass.
- Audit coverage must include export creation.

## Routes

- `GET /api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>`
- `GET /api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/summary`
- `GET /api/v1/dossier-builder/v3/export-gate/<case_id>/<subject_id>/decision`

## Merge gate

Full CI must pass before merge.
