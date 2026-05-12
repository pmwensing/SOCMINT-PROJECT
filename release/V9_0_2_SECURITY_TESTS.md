# SOCMINT v9.0.2 — Automated Security Test Pack

## Summary

Adds automated security-audit helpers and test coverage for the post-v9 hardening path.

## Added

- Secret-pattern scanner helper.
- Secret value validator.
- Security header expectations helper.
- Session cookie expectations helper.
- Security audit admin routes.
- Hardening route integration.
- Focused v9.0.2 security tests.

## New API surfaces

- `GET /api/v1/admin/security/audit`
- `GET /api/v1/admin/security/secrets/scan`
- `GET /api/v1/admin/security/headers`
- `GET /api/v1/admin/security/cookies`
- `GET /api/v1/admin/security/secret-key`

## Merge gate

Full CI must pass before merge.

## Next target

v9.0.3 — Route Enforcement Test Matrix.
