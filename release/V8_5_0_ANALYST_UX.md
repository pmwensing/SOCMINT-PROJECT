# SOCMINT v8.5.0 — Analyst UX Polish

## Summary

Adds an analyst launchpad layer that summarizes operational readiness without changing core dossier, billing, production, or connector behavior.

## Added

- Analyst launchpad payload helper.
- Compact launchpad payload helper.
- Readiness cards for cases, review queue, captures, jobs, connectors, membership, and production readiness.
- Next-action hints for export blockers, failed jobs, connector reliability, free plan limits, billing grace, and export readiness.
- Launchpad API routes.
- Launchpad UI template.
- WSGI route registration.

## Routes

- `GET /analyst/launchpad`
- `GET /api/v1/analyst/launchpad`
- `GET /api/v1/analyst/launchpad/compact`

## Validation

Full CI must pass before merge.

## Next target

v8.6.0 — Export/Dossier Superiority.
