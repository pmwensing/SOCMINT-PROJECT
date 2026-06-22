# v31.3 — Editorial Validation and Policy Gate

## Objective

Evaluate draft dossier revisions for editorial completeness, provenance integrity, policy acknowledgements, release-scope requirements, and unresolved blockers before any human release approval may be requested.

## Delivered

- append-only editorial validation records
- deterministic validation identifiers and hashes
- immutable binding to the draft revision, publication candidate, source manifest, and section snapshot
- checks for draft state, candidate state, candidate hash consistency, source manifest, section snapshot, contribution entry, target section, assembly gaps, and dossier readiness
- required provenance, privacy, legal-basis, and audience-scope acknowledgements
- mandatory redaction review for external, public, or third-party release scopes
- `passed` and `needs_revision` gate outcomes
- administrator-only editorial validation APIs
- editorial validation inventory in the Publication Review Workspace
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/editorial-validations`
- `GET /api/v1/publication-review/draft-revisions/<draft_revision_id>/editorial-validations`
- `POST /api/v1/publication-review/draft-revisions/<draft_revision_id>/editorial-validations`

## Safety boundaries

- draft revision and publication candidate remain immutable
- a passing gate does not approve release
- no publication
- no published revision mutation
- no database migration

## Next action

Implement v31.4 Human Release Approval.
