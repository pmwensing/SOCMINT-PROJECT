# SOCMINT v10.8.0 — Export Audit Auto-Hooks

## Summary

Wires dossier export audit events directly into export creation, manifest reads, and download resolution workflows.

## Changes

- Adds optional audit hooks to `persist_export_pack`.
- Adds optional audit hooks to `load_export_manifest`.
- Adds optional audit hooks to `resolve_export_download_path`.
- Wires authenticated export-store routes to record actor-aware audit events.
- Wires authenticated export-download route to record actor-aware download audit events.
- Adds focused v10.8 audit-hook tests.

## Audit events

- `export_created`
- `manifest_read`
- `download_resolved`
- `download_blocked`
- `download_missing`

## Merge gate

Full CI must pass before merge.
