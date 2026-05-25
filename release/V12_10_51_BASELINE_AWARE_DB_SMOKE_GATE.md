# v12.10.51 — Baseline-Aware DB Smoke Gate

Purpose:
1. Correct v12.10.38/v12.10.39 lingering-table false positive.
2. Build temp SQLite DB at `0017_v12_10_schema_reconciliation`.
3. Record baseline tables.
4. Upgrade temp DB to head / `0018_approved_model_migration`.
5. Confirm all approved tables exist after upgrade.
6. Determine true 0018-owned tables as approved tables not present at 0017.
7. Downgrade back to `0017_v12_10_schema_reconciliation`.
8. Confirm only true 0018-owned tables are removed.
9. Allow baseline-approved tables to remain after downgrade.
10. Do not run real configured DB upgrade.
11. Do not touch production DB.
