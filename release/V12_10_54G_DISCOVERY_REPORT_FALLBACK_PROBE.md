# v12.10.54G — Discovery Report Fallback Probe App

Purpose:
1. Keep the passing runtime adapter tests intact.
2. Fix direct report execution where app discovery crashes before endpoint probing.
3. Try real dashboard app first.
4. If dashboard app discovery fails, create an isolated Flask probe app and register the same v12.10.54 routes.
5. Verify the five hardening endpoints either through real runtime app or isolated fallback route probe.
6. Record whether verification mode was `dashboard_runtime` or `isolated_probe`.
7. Keep real DB upgrade blocked by default.
8. Do not run real DB upgrade.
9. Do not touch production DB.
