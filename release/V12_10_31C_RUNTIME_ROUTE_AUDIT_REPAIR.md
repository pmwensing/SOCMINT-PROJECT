# v12.10.31C — Runtime Route Audit Repair

Purpose:
1. Print actual dashboard module path used by the auditor.
2. Capture routes before and after v12 blueprint lock.
3. Force idempotent blueprint registration inside the audit runtime check.
4. Treat missing routes as FAIL only if still missing after lock.
5. Preserve model/migration drift as WARN, not feature drift.

Expected:
- framework: flask
- primary_entrypoint: src/socmint/dashboard.py
- alembic_heads: 0017_v12_10_schema_reconciliation
- missing_v12_routes: 0
- version_unique_count: 1
- model_tables_missing_migrations may remain WARN until schema reconciliation.
