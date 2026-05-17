# v11.4 — Command Center Test Data Controls + Operator QA Dashboard

## Purpose

v11.4 turns the v11.3 smoke-data cleanup system into an operator-visible Command Center capability.

## Added

- `src/socmint/test_data_controls.py`
- `/api/v1/admin/test-data/summary`
- `/api/v1/admin/test-data/clean`
- `/command-center/test-data/clean`
- Command Center `test_data` payload block
- Command Center Test Data Hygiene panel
- Per-subject `is_test_data` badge for `v11-smoke-*` records
- `scripts/test_v11_4.sh`

## Operator controls

The Command Center now shows:

- Smoke/test subject count
- Smoke dossier export files
- Smoke artifact directories
- Smoke seeds, connector runs, observations, assertions, validation events, and account discoveries
- A browser cleanup action for authorized operators
- A JSON summary endpoint for automation

## Validation

Run:

```bash
./scripts/test_v11_4.sh
```

Or, after adding the local Makefile target:

```bash
make test-v11-4
```

Expected:

```text
PASS command center test data controls smoke v11.4
```

## Notes

This release does not perform live external OSINT calls. It creates a deterministic `v11-smoke-*` subject, verifies the Command Center and JSON API expose it as test data, then cleans it with the same backend cleanup service used by the UI/API.
