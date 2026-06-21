# v31.1 — Publication Candidate Contract

## Objective

Create append-only publication candidates only from explicitly approved v30 dossier contributions.

## Delivered

- deterministic publication candidate identifiers and hashes
- immutable binding to the approved dossier contribution, claim, case, entity, and target section
- explicit publication purpose, release scope, rationale, confirmation, and administrative reason
- administrator-only candidate APIs
- append-only candidate history
- proposed-to-withdrawn state transition only
- candidate inventory in the Publication Review Workspace
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/candidates`
- `POST /api/v1/publication-review/candidates`
- `GET /api/v1/publication-review/contributions/<dossier_contribution_id>/candidates`
- `POST /api/v1/publication-review/candidates/<candidate_id>/state`

## Safety boundaries

- approved v30 dossier contribution required
- no draft dossier revision creation
- no release approval
- no publication
- no contribution or dossier mutation
- no database migration

## Next action

Implement v31.2 Draft Dossier Revision Assembly.
