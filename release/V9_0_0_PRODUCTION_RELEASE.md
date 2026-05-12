# SOCMINT v9.0.0 — Production Release

## Summary

Finalizes the v8.2 through v8.7 productization sequence as a v9 production release marker.

## Included milestones

- v8.2.0 Membership + Quotas
- v8.3.0 Billing Bridge
- v8.4.0 Production Access Readiness
- v8.5.0 Analyst UX Polish
- v8.6.0 Export Quality
- v8.7.0 Connector SDK + Marketplace
- v9.0.0 Production Release

## Added

- Production release readiness helper.
- Production release summary helper.
- Production release API routes.
- WSGI route registration.
- Final production release checklist.

## Routes

- `GET /api/v1/production-release`
- `GET /api/v1/production-release/summary`

## Definition of done

- CI green.
- Migration smoke green.
- Backup restore smoke green.
- Production boot smoke green.
- Dependency audit green.
- Release checklist present.

## Merge gate

Full CI must pass before merge.
