# v31.2 — Draft Dossier Revision Assembly

## Objective

Create deterministic, append-only draft dossier revisions from proposed publication candidates while preserving the existing dossier pipeline as the authoritative source.

## Delivered

- deterministic draft revision identifiers and hashes
- immutable source manifest binding the publication candidate, approved contribution, case, subject, source package, sections, and gaps
- captured dossier assembly section snapshot
- explicit candidate contribution entry for the target dossier section
- revision label, editorial note, confirmation, and administrative reason requirements
- administrator-only draft revision APIs
- draft revision inventory in the Publication Review Workspace
- focused model and route tests

## Routes

- `GET /api/v1/publication-review/draft-revisions`
- `GET /api/v1/publication-review/candidates/<candidate_id>/draft-revisions`
- `POST /api/v1/publication-review/candidates/<candidate_id>/draft-revisions`

## Safety boundaries

- proposed publication candidate required
- source package and dossier assembly remain immutable
- no release approval
- no publication
- no published revision mutation
- no database migration

## Next action

Implement v31.3 Editorial Validation and Policy Gate.
