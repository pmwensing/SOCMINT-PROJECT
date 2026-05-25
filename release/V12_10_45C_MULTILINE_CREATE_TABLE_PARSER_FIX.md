# v12.10.45C — Multiline create_table Parser Fix

Purpose:
- Fix v12.10.45B parser failure.
- Detect both:
  - `op.create_table("table", ...)`
  - `op.create_table(\n    "table", ...`
- Re-run blocked identity table repair safely.
- Do not touch production DB.
- Do not run real configured DB upgrade.
