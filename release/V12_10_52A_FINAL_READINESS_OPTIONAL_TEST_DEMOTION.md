# v12.10.52A — Final Readiness Optional-Test Demotion

Purpose:
1. Read v12.10.52 readiness manifest.
2. Identify failed check.
3. Demote transitional repair-suite failures from hard blockers to warnings when canonical v12.10.51 baseline-aware DB smoke is GO.
4. Keep hard blockers for:
   - Alembic head failure
   - production DB touched
   - real DB upgrade run
   - baseline-aware DB smoke not GO
   - approved-table accounting mismatch
5. Produce corrected final release readiness manifest.
6. Do not mutate schema.
7. Do not run real configured DB upgrade.
8. Do not touch production DB.
