# SOCMINT v8.4.0 — Production Access

## Summary

Adds a production access readiness layer with safe service-status tracking, deployment config generation, and health checks.

## Added

- Service status helper.
- Config snippet generator.
- Production environment template.
- Readiness checks.
- Secret-safety guardrail.
- Service status persistence table.
- Status/readiness/admin API routes.
- Alembic migration `0012_tor_status`.
- v8.4 production access tests.

## Validation

```bash
PYTHONPATH=$PWD/src pytest -q tests/test_tor_production_v8_4.py
```

## Next target

v8.5.0 — Analyst UX Polish.
