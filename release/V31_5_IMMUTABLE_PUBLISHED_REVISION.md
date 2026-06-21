# v31.5 — Immutable Published Revision

## Objective

Create a sealed, append-only published dossier revision only after explicit v31.4 human release approval.

## Delivered

- deterministic published revision identifiers and SHA-256 hashes
- immutable published content snapshot
- provenance binding to the draft revision, publication candidate, approved contribution, editorial validation, source manifest, and human release approval
- integrity hashes for content, provenance, and metadata
- the latest human release decision must be approved and match the current draft revision
- one-time use of each release approval
- administrator-only publication APIs
- case-level publication history inventory
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/published-revisions`
- `GET /api/v1/publication-review/cases/<case_id>/published-revisions`
- `POST /api/v1/publication-review/draft-revisions/<draft_revision_id>/published-revisions`

## Safety boundaries

- approved human release decision required
- explicit publication confirmation required
- no draft or approval mutation
- no prior published revision mutation
- no external transmission
- supersession is not performed in this slice
- no database migration

## Next action

Implement v31.6 Supersession and Revision History.
