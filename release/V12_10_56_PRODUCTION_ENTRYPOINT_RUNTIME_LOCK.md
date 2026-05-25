# v12.10.56 — Production Entrypoint Discovery + Runtime Mount Lock

Purpose:
1. Inspect Dockerfile/docker-compose/Makefile/pyproject for actual runtime command.
2. Detect Flask app module/object or factory from configured runtime entrypoint.
3. Refuse PASS if only isolated_probe verifies.
4. Mount v12.10.54 routes into true configured runtime app.
5. Generate production entrypoint report.
6. Generate route map from configured runtime only.
7. Keep isolated_probe as WARN fallback, not GO.
8. Do not run real DB upgrade.
9. Do not touch production DB.
