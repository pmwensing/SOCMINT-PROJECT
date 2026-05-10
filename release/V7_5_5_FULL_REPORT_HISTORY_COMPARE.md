# SOCMINT v7.5.5 — Full Report Export History + Compare Previous Reports

## Added

- Full-report export history discovery.
- Previous-vs-latest report comparison helper.
- Browser-facing export history page.
- API endpoints for history and compare.
- Dossier UI links for:
  - Export History
  - Compare Previous Reports
- Runtime smoke for generating multiple reports and comparing them.
- `make test755` and `make zip755`.

## New routes

- `GET /api/v1/spine/subjects/{subject_id}/full-report/history`
- `GET /api/v1/spine/subjects/{subject_id}/full-report/compare`
- `GET /spine/subjects/{subject_id}/full-report/history`

## Compare output

The compare payload reports:

- selected previous export
- selected latest export
- dossier score deltas
- artifact role additions/removals/unchanged roles

## Runtime smoke

The v7.5.5 smoke test performs:

1. Generate two full-report exports for a test subject.
2. Build export history.
3. Compare previous-vs-latest.
4. Compare explicit named exports.
5. Register alias, browser, and history routes.
6. Simulate authenticated admin session.
7. Verify history API.
8. Verify compare API.
9. Verify browser history panel.
10. Run existing dossier regression tests.

## Validate

```bash
make test755
```
