# v11.5 — Legacy Absolute Import Cleanup + Docker Runtime Stability

## Purpose

v11.5 hardens Docker runtime boot by detecting legacy absolute `socmint` imports that break when the package is loaded as `src.socmint`.

## Added

- `src/socmint/runtime_import_health.py`
- `/api/v1/admin/runtime/import-health`
- Command Center runtime import health payload block
- Command Center runtime import health status card
- `scripts/test_v11_5.sh`

## Behavior

The runtime import health report performs:

1. Source scan for `import socmint` and `from socmint` inside `src/socmint`.
2. Package import probe across `src.socmint` modules.
3. Failure capture for `No module named 'socmint'` import errors.
4. Command Center surfacing through `runtime_import_health`.
5. Authenticated JSON reporting at `/api/v1/admin/runtime/import-health`.

## Validation

Run:

```bash
make test-v11-5
```

Expected:

```text
PASS runtime import health direct
PASS runtime import health API and command center payload
PASS Docker runtime import stability smoke v11.5
```

## Docker log gate

The v11.5 smoke fails if app logs contain:

```text
No module named 'socmint'
```

## Notes

This release is a hardening build. It does not add live OSINT behavior. It makes legacy route/module registration safer to verify before the next feature build.
