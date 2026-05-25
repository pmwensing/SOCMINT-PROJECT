# v12.10.55 — Real Runtime Route Mount Verification

Purpose:
1. Keep v12.10.54G isolated probe PASS as fallback.
2. Identify why dashboard_runtime discovery fails in direct report mode.
3. Find the true production Flask entrypoint used by Docker/uvicorn/gunicorn/flask.
4. Mount v12.10.54 routes in the real runtime entrypoint, not just isolated probe.
5. Add route-map report showing actual runtime rules.
6. Verify `/api/version` and `/api/schema/status` through real runtime app.
7. Preserve upgrade guard default block.
8. Do not run real DB upgrade.
9. Do not touch production DB.

Safety:
- No Alembic upgrade.
- No real configured DB migration.
- No production DB mutation.
