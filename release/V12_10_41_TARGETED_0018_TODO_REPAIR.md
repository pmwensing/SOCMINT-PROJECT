# v12.10.41 — Targeted 0018 TODO Placeholder Repair + DB Smoke Recheck

Purpose:
- Repair v12.10.40 blocker: executable TODO placeholders in promoted 0018 migration.
- Patch only:
  - `migrations/versions/0018_approved_model_migration.py`
  - draft/generator files if needed
- Convert executable TODO placeholders to safe SQLAlchemy defaults.
- Preserve TODO review notes as comments.
- Rerun dry-run DB smoke against temp SQLite only.
- Rerun DB smoke result gate.
- Do not touch production DB.
- Do not run real configured DB upgrade.
