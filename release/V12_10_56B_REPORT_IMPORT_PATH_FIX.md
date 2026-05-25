# v12.10.56B — Production Entrypoint Report Import Path Fix

Purpose:
1. Fix direct `make report121056A` failure: `ModuleNotFoundError: No module named 'src'`.
2. Add repo root to `sys.path` inside the report script.
3. Preserve v12.10.56A production WSGI entrypoint shim behavior.
4. Re-run production entrypoint route-lock report.
5. Do not run real DB upgrade.
6. Do not touch production DB.
