# v12.10.47 — Identity Table Constraint Neutralizer + DB Smoke Recheck

Purpose:
1. Use v12.10.46 diagnostics if present.
2. Patch only the existing identity table blocks in promoted 0018:
   - `all_tab_identity_cols`
   - `identity_columns`
3. Neutralize SQLite-smoke-hostile patterns:
   - table-level constraints
   - extra primary keys
   - foreign keys
   - server defaults
   - executable TODO placeholders
   - dialect-specific types
4. Preserve review notes as TODO comments.
5. Rerun temp SQLite DB smoke.
6. Rerun DB smoke gate and exact locator.
7. Do not run real configured DB upgrade.
8. Do not touch production DB.
