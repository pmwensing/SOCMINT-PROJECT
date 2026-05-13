# SOCMINT v10.2.0 — Production Installer + Local Rebuild Pack

## Summary

Adds a conservative production installer and local rebuild documentation pack.

## Changes

- Adds production installer readiness helpers.
- Adds admin installer readiness API routes.
- Adds `scripts/install_production.sh`.
- Adds `.env.production.example`.
- Adds local rebuild guide.
- Adds production deployment pack.
- Adds focused v10.2 installer tests.

## Routes

- `GET /api/v1/admin/installer/plan`
- `GET /api/v1/admin/installer/readiness`
- `GET /api/v1/admin/installer/readiness/summary`

## Merge gate

Full CI must pass before merge.
