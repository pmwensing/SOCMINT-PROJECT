# v12.10.44 — Iterative DB Smoke Repair Loop

Purpose:
1. Run the v12.10.43 targeted failed-table repair repeatedly.
2. After each repair, rerun v12.10.38 temp SQLite DB smoke.
3. Rerun v12.10.39 DB smoke result gate.
4. Rerun v12.10.42 exact failure locator if smoke remains NO-GO.
5. Stop when DB smoke becomes GO or max repair passes is reached.
6. Do not run real DB upgrade.
7. Do not touch production DB.
8. Produce loop manifest and release decision.

Safety:
- Temp SQLite only.
- No real configured DB upgrade.
- No production DB touched.
