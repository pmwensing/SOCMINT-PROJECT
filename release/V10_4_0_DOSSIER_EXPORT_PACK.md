# SOCMINT v10.4.0 — Dossier Export Pack v1

## Summary

Adds deterministic JSON and HTML export-pack generation for dossier builder v3 payloads.

## Changes

- Adds dossier export pack core helpers.
- Adds export preflight validation.
- Adds canonical JSON rendering.
- Adds HTML rendering with escaping.
- Adds artifact manifest and SHA-256 hashes.
- Adds export pack API routes.
- Registers export routes through the production release route module.
- Adds focused v10.4 export pack tests.

## Routes

- `POST /api/v1/dossier-builder/v3/export-pack`
- `POST /api/v1/dossier-builder/v3/export-pack/summary`

## Merge gate

Full CI must pass before merge.
