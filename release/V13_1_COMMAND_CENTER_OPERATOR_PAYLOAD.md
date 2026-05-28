# v13.1 — Command Center Operator Payload

## Purpose

This release wires the v13 next-action engine into the command-center payload used by the web UI and API.

## Added

- `payload.operator` on the command-center page payload.
- `payload.operator.dossier_readiness`.
- `payload.operator.next_best_action`.
- `payload.operator.operator_flow`.

## Routes affected

- `GET /command-center`
- `GET /api/v1/command-center`
- `GET /api/v1/command-center/next-action`

## Value

The UI can now render one clear operator action without separately calling the next-action API.

This keeps the existing command-center page stable while preparing the visible UI for the clean v13 operator workflow.
