# SOCMINT v9.0.1 — Hardening Audit Bundle

## Summary

Adds the first post-v9 hardening bundle focused on gate visibility, export preflight enforcement, and security checklist reporting.

## Added

- Route gate audit matrix helper.
- Gate audit summary helper.
- Export preflight gate helper.
- Export preflight summary helper.
- Security hardening checklist helper.
- Hardening API route module.
- Production-release route integration for the hardening routes.

## New API surfaces

- `GET /api/v1/admin/gates/matrix`
- `GET /api/v1/admin/gates/summary`
- `GET /api/v1/admin/security/checklist`
- `GET /api/v1/spine/subjects/<subject_id>/export-preflight`
- `GET /api/v1/spine/subjects/<subject_id>/export-preflight/summary`

## Notes

Hardening routes are registered through the existing production-release route module, which is already wired into the WSGI app.

## Merge gate

Full CI must pass before merge.
