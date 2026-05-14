# SOCMINT v10.19.0 — Release Distribution Audit Trail + Operator Handoff Packet

## Summary

Adds a case-level operator handoff packet for distribution releases. The packet rolls up release ledger entries, release seal statements, verification summaries, ZIP hashes, operator links, and release-state counts into JSON and markdown outputs.

## Focus

The handoff packet answers:

- Which subjects are released, ready to seal, or held?
- Which ZIP hashes and seal IDs were released?
- Which verification status supports each release?
- Which links should the next operator use for download, verification, release state, and seal statements?
- What final markdown report can be handed off with the case?

## Changes

- Adds `src/socmint/distribution_handoff_packet.py`.
- Adds `src/socmint/distribution_handoff_packet_routes.py`.
- Registers handoff routes in `src/socmint/wsgi.py`.
- Adds handoff links to `src/socmint/templates/release_ledger_dashboard.html`.
- Adds `tests/test_distribution_handoff_packet_v10_19.py`.
- Adds `scripts/test_v10_19.sh`.

## Routes

- `GET /api/v1/dossier-builder/v3/distribution-handoff/<case_id>`
- `GET /api/v1/dossier-builder/v3/distribution-handoff/<case_id>/markdown`

## Merge gate

Run:

```bash
bash scripts/test_v10_19.sh
```
