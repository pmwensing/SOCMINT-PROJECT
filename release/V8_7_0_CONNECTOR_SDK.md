# SOCMINT v8.7.0 — Connector SDK + Marketplace

## Summary

Adds a connector SDK validation and marketplace metadata layer without changing existing connector execution.

## Added

- Connector manifest generation.
- Connector spec validation.
- Catalog hash generation.
- SDK fixture-run validator.
- Marketplace SDK payload.
- SDK API routes.
- WSGI route registration.

## Routes

- `GET /api/v1/connectors/sdk/catalog`
- `GET /api/v1/connectors/sdk/marketplace`
- `POST /api/v1/connectors/sdk/validate`
- `POST /api/v1/connectors/sdk/fixture-run`

## Merge gate

Full CI must pass before merge.

## Next target

v9.0.0 — Production Release.
