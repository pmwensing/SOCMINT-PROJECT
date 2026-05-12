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
- Registration helper for hardening routes.

## New API surfaces

- `GET /api/v1/admin/gates/matrix`
- `GET /api/v1/admin/gates/summary`
- `GET /api/v1/admin/security/checklist`
- `GET /api/v1/spine/subjects/<subject_id>/export-preflight`
- `GET /api/v1/spine/subjects/<subject_id>/export-preflight/summary`

## Important note

The WSGI file update was blocked by the connector filter during remote patching. The route module and registration helper are included. Final direct WSGI registration should be confirmed before production use.

## Recommended next local patch

Add this to `src/socmint/wsgi.py`:

```python
from .hardening_routes import register_hardening_routes
...
register_hardening_routes(app)
```

## Merge gate

Full CI must pass before merge.
