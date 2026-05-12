# SOCMINT v8.6.0 — Export Quality

## Summary

Adds an export-quality layer for Ultimate Dossier outputs. This is additive and does not replace the existing dossier/export builder.

## Added

- Export quality score and grade.
- JSON/CSV assertion parity checks.
- Redaction coverage summary.
- Dossier readiness integration.
- Traceability coverage summary.
- Confirmed-assertion coverage summary.
- Export quality API routes.
- WSGI route registration.

## Routes

- `GET /api/v1/spine/subjects/<subject_id>/export-quality`
- `GET /api/v1/spine/subjects/<subject_id>/export-quality/summary`

## Merge gate

Full CI must pass before merge.

## Next target

v8.7.0 — Connector SDK + Marketplace.
