# v31.0 — Publication Review Workspace

The read-only Publication Review Workspace is implemented on the Ruff-clean `master` baseline.

## Delivered

- approved v30 dossier-contribution inventory
- dossier assembly, export, release, and delivery contract inventory
- draft and published revision inventory
- publication blockers and readiness findings
- administrator-only UI and API
- focused tests

## Routes

- `GET /publication-review`
- `GET /api/v1/publication-review`

## Validation

- CI lint: passed
- CI test suite: passed
- command-center export verification: passed
- Compose, migration, backup, production boot, and dependency checks: passed
- SOCMINT Full Verification: passed
- v12.10.19 verification: passed

## Safety

- no automatic publication
- no release approval
- no dossier mutation
- no migration

Next action: v31.1 Publication Candidate Contract.
