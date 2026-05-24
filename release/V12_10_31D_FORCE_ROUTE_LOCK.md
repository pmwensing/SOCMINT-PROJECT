# v12.10.31D — Force Route Lock When Blueprint Name Exists But Rules Missing

Problem:
- The standalone drift auditor reports `missing_v12_routes: 8`.
- Runtime tests can load the routes, but the audit runtime can see blueprint names without actual expected route rules.
- Previous lock skipped registration when `bp.name in app.blueprints`, even if route rules were absent.

Fix:
- If expected v12 routes are missing, force-register the blueprint using a unique alias name.
- This bypasses stale blueprint-name collisions while preserving idempotence.
- Model/migration drift remains a WARN, not a route/runtime failure.
