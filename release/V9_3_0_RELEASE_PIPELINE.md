# SOCMINT v9.3.0 — Production Docker/Tor Release Pipeline

## Summary

Adds a production release pipeline readiness layer for Docker/Tor release rehearsals, deployment smoke documentation, and release artifact expectations.

## Added

- Release pipeline readiness helper.
- Release pipeline summary helper.
- Manual release workflow spec helper.
- Admin release pipeline API routes.
- Production-release route integration.
- Focused v9.3 release pipeline tests.

## New API surfaces

- `GET /api/v1/admin/release-pipeline`
- `GET /api/v1/admin/release-pipeline/summary`
- `GET /api/v1/admin/release-pipeline/workflow`

## Merge gate

Full CI must pass before merge.

## Next target

v9.4.0 — Public Beta Readiness.
