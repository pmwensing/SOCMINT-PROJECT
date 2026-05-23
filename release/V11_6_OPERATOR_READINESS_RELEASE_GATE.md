# v11.6 — Command Center Operator Readiness + Release Gate Dashboard

## Purpose

v11.6 turns the v11.1–v11.5 verification chain into one operator-facing readiness gate in the Command Center.

## Added

- `src/socmint/v11_readiness.py`
- `/api/v1/admin/v11/readiness-summary`
- Command Center `v11_readiness` payload block
- Command Center `v11 Readiness` dashboard section
- Release gate report JSON
- `scripts/test_v11_6.sh`

## Readiness checks

The v11 readiness summary combines:

1. Frontend route audit harness presence.
2. Subject workflow and dossier-generation smoke presence.
3. Test-data hygiene status.
4. Runtime import health status.
5. Tor hidden-service readiness.
6. Worker queue status.

## Release gate

The API returns:

- `status`
- `ready`
- `passed_checks`
- `total_checks`
- `percentage`
- `next_action`
- `checks`
- `blocking_checks`
- `release_gate`

## Validation

Run:

```bash
make test-v11-6
```

Expected:

```text
PASS v11.6 readiness direct payload
PASS v11.6 operator readiness release gate smoke
```

## Notes

Some readiness checks are state-based. For example, Tor readiness depends on the local Docker/Tor registration status, and worker readiness depends on failed/stale jobs. A `needs_review` status is therefore allowed by the smoke as long as the schema, checks, and release gate are present and internally consistent.
