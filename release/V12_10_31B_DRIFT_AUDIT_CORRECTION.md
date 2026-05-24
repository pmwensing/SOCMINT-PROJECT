# v12.10.31B — Drift Audit Correction + Runtime Route Lock

Purpose:
- Stop the drift auditor from selecting itself as the primary app entrypoint.
- Re-lock v12.10 runtime route registration on the real Flask app factory.
- Normalize release manifest/version metadata for v12.10.31B.
- Keep model-vs-migration drift visible as a warning until a dedicated schema reconciliation patch is built.

Expected:
- Framework: hybrid or flask
- Primary entrypoint: src/socmint/dashboard.py
- Alembic head: 0017_v12_10_schema_reconciliation
- Missing v12 routes: 0
