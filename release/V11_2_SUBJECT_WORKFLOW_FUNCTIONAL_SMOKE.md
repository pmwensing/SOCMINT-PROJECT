# v11.2 — Subject Workflow Functional Smoke + Dossier Generation QA

## Purpose

v11.2 adds a deterministic local functional smoke test for the core v11 analyst workflow:

1. Create a Spine subject.
2. Add a seed.
3. Create a deterministic connector run without live external OSINT calls.
4. Register a raw artifact with SHA-256.
5. Create an observation.
6. Create and confirm a dossier assertion.
7. Create an account discovery record.
8. Export a Full Entity Profile Dossier v2 package.
9. Verify export history.
10. Verify the Command Center sees the subject and latest report.

## Added

- `scripts/test_subject_workflow_v11_2.sh`
- `make test-subject-workflow-v11-2`
- `make test-v11-2`

## Validation

Run:

    make test-v11-2

Expected:

    PASS frontend route audit v11.1.1
    PASS subject workflow functional smoke v11.2

## Notes

This smoke intentionally avoids live external connector calls. It validates the internal workflow and dossier/export surfaces deterministically so it can run on a laptop, in CI-like local environments, and behind Tor/Docker without network dependency.
