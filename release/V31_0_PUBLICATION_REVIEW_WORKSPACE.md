# v31.0 — Publication Review Workspace

## Objective

Provide a read-only publication-readiness view over approved v30 dossier contributions and the existing dossier assembly, export, release, and delivery contracts.

## Delivered

- administrator-only Publication Review Workspace
- JSON publication-review API
- approved v30 dossier-contribution inventory
- existing dossier contract inventory
- draft and published revision inventory derived from existing release history
- release action counts and case coverage
- blockers for missing case bindings, missing target sections, and missing dossier contracts
- publication-readiness findings
- route integration through the existing analytic product-review registration chain
- focused workspace and route tests

## Routes

- `GET /publication-review`
- `GET /api/v1/publication-review`

## Safety boundaries

- read-only workspace
- no publication candidate creation
- no draft assembly
- no human release approval
- no automatic publication
- no dossier or published revision mutation
- no connector execution
- no database migration

## Validation

The branch is rebased onto the Ruff-clean `master`; CI and project regression validation are authoritative.

## Next action

Implement v31.1 Publication Candidate Contract.
