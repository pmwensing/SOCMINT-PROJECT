# v11.3 — Test Data Hygiene + Workflow Cleanup + Re-run Stability

## Purpose

v11.3 makes the v11 workflow smoke tests safe to run repeatedly on a laptop or CI-like environment without leaving long-lived smoke subjects, artifacts, or dossier exports behind.

## Added

- `scripts/clean_v11_smoke_data.sh`
- `scripts/test_subject_workflow_v11_3.sh`
- `make clean-v11-smoke`
- `make test-subject-workflow-v11-3`
- `make test-v11-3`

## Behavior

The v11.3 smoke test:

1. Cleans prior `v11-smoke-*`, `v11.2-smoke-*`, and `v11.3-smoke-*` test subjects.
2. Creates a new `v11-smoke-*` subject.
3. Adds a deterministic local seed.
4. Creates a connector run without external OSINT calls.
5. Tags raw artifacts and payloads as test data.
6. Creates observation/assertion/account-discovery records.
7. Exports the full entity dossier twice.
8. Verifies export history is re-run safe.
9. Verifies Command Center can see the subject and latest report.
10. Cleans test data again.

## Validation

Run:

```bash
make test-v11-3
```

Expected:

```text
PASS frontend route audit v11.1.1
PASS subject workflow functional smoke v11.2
PASS v11.3 test data hygiene and re-run stability
```

## Notes

This test avoids live external connector calls. It validates local workflow correctness, export generation, history stability, Command Center surfacing, and cleanup hygiene.
