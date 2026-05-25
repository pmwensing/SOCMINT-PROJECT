# v12.10.38 — Dry-Run DB Migration Smoke

Purpose:
1. Create temporary isolated SQLite database.
2. Run `alembic upgrade head` against temp DB only.
3. Verify 0018 approved tables exist.
4. Verify downgrade path back to 0017 works.
5. Verify no production DB touched.
6. Generate DB smoke report.
7. Still do not run upgrade on real configured DB.

Guarantees:
- Uses temp SQLite database under `/tmp`.
- Uses temp Alembic config.
- Exports common DB URL environment variables to temp SQLite only.
- Does not run upgrade against the configured production/dev database.
