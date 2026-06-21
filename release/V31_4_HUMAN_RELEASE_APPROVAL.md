# v31.4 — Human Release Approval

## Objective

Require an explicit human decision before a validated draft dossier revision may become eligible for immutable publication.

## Delivered

- append-only human release decisions
- deterministic approval identifiers and hashes
- immutable binding to the draft revision, passing editorial validation, publication candidate, source manifest, and section snapshot
- decisions: approve, return, and hold
- explicit confirmation, reviewer identity, note, and administrative reason
- approval blocked unless the latest validation matches the current draft revision
- approve requires a passing editorial validation
- administrator-only release approval APIs
- human release decision inventory in the Publication Review Workspace
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/release-approvals`
- `GET /api/v1/publication-review/draft-revisions/<draft_revision_id>/release-approvals`
- `POST /api/v1/publication-review/draft-revisions/<draft_revision_id>/release-approvals`

## Safety boundaries

- approval does not publish anything
- no published revision is created in this slice
- draft revision and editorial validation remain immutable
- return and hold never enable publication
- no database migration

## Next action

Implement v31.5 Immutable Published Revision.
