# SOCMINT v10.1.2 — Release Integrity + Route Registration Audit

## Summary

Adds final release integrity reporting for the v10.1 line.

## Changes

- Updates version metadata to `10.1.2`.
- Adds release integrity report helper.
- Adds release integrity summary helper.
- Adds route registration audit helper.
- Adds admin release integrity API routes.
- Registers release integrity routes through the production release route module.
- Adds focused release integrity tests.

## Routes

- `GET /api/v1/admin/release-integrity/report`
- `GET /api/v1/admin/release-integrity/summary`
- `GET /api/v1/admin/release-integrity/routes`

## Merge gate

Full CI must pass before merge.
