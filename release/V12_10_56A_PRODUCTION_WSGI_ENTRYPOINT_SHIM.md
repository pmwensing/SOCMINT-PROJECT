# v12.10.56A — Production WSGI Entrypoint Shim + Runtime Lock

Purpose:
1. Treat v12.10.56 `selected_spec=null` as a real production-entrypoint gap.
2. Add a deterministic production WSGI entrypoint at `src.socmint.wsgi:app`.
3. Build the WSGI app from the discovered dashboard runtime when possible.
4. If dashboard runtime discovery fails, create a minimal Flask runtime app with v12.10.54 guard routes mounted.
5. Mark fallback mode clearly as `wsgi_guard_minimal`, not `isolated_probe`.
6. Verify `/api/version`, `/api/schema/status`, `/api/schema/upgrade-guard`, `/api/release/archive-integrity`, and `/api/schema/rollback/0018` through `src.socmint.wsgi:app`.
7. Update production entrypoint route-lock report to require a configured spec, not isolated probe.
8. Do not run real DB upgrade.
9. Do not touch production DB.
