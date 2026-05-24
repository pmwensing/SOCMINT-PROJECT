# v12.10.31F — Clean Drift Auditor Rewrite

Problem:
- Imported auditor route-smoke tests pass.
- Standalone `python scripts/drift_lock_audit_v12_10_31A.py` still reports missing v12 routes.
- This means the patch-stacked audit script has divergent code paths.

Fix:
- Replace the audit script with a clean deterministic implementation.
- Use one route-check function for both tests and standalone execution.
- Treat model/migration mismatch as WARN, not route/runtime FAIL.
- Produce one authoritative report: `DRIFT_LOCK_AUDIT_V12_10_31F`.
